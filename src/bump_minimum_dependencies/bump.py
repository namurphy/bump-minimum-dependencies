__all__ = ["Package"]


import requests
from packaging.requirements import Requirement

from dep_logic.specifiers import parse_version_specifier
import collections
import warnings

from datetime import datetime, timedelta, date

from packaging.version import Version, InvalidVersion

from pyproject_parser import PyProject

import logging

import math

import subprocess
import functools


DAYS_PER_MONTH = 30.436875


def format_version(version: Version | str) -> str:
    """Make the version a string and remove '.0' suffixes."""
    v = str(version).strip()
    while v.endswith(".0"):
        v.removesuffix(".0")
    return v


class Package:
    def __init__(self, name):
        self.name = name
        self.get_release_dates()
        self.today = datetime.now().date()

    def get_release_dates(self) -> None:
        response = requests.get(
            url=f"https://pypi.org/simple/{self.name}",
            headers={"Accept": "application/vnd.pypi.simple.v1+json"},
        ).json()

        file_date = collections.defaultdict(list)
        for file in response["files"]:
            ver = file["filename"].split("-")[1]
            try:
                version = Version(ver)
            except InvalidVersion as e:
                logging.debug(
                    f"'{ver}' is an invalid version for '{self.name}'. Reason: {e}"
                )
                continue

            if version.is_prerelease:
                logging.debug(
                    f"Excluding {ver} for {self.name} since it is a prerelease"
                )
                continue

            release_date = None
            for format_ in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"]:
                try:
                    release_date = datetime.strptime(file["upload-time"], format_)
                except ValueError as e:
                    logging.debug(f"Invalid date: {e}")

            if not release_date:
                continue

            file_date[version].append(release_date.date())

        release_date = {version: min(file_date[version]) for version in file_date}

        self._release_dates: dict[Version, date] = {}
        for version, release_date in release_date.items():
            self._release_dates[version] = release_date

    @property
    def release_dates(self) -> dict[Version, date]:
        """..."""
        return self._release_dates

    @functools.cached_property
    def releases(self) -> list[Version]:
        """..."""
        return sorted(self.release_dates)

    @functools.cached_property
    def _epoch_major_minor_to_set_of_micro(
        self,
    ) -> dict[tuple[int, int, int], set[int]]:
        """
        Dictionary where the key is a tuple of the major and minor version numbers,
        and
        """
        epoch_major_minor_to_set_of_micro = {}

        for version in self.releases:
            epoch = version.epoch
            major = version.major
            minor = version.minor
            micro = version.micro

            if (epoch, major, minor) not in epoch_major_minor_to_set_of_micro:
                epoch_major_minor_to_set_of_micro[(epoch, major, minor)] = {micro}
            else:
                epoch_major_minor_to_set_of_micro[(epoch, major, minor)] |= {micro}

        return epoch_major_minor_to_set_of_micro

    @functools.cached_property
    def minor_releases(self) -> list[Version]:
        """The first release of each major/minor pair."""
        minor_releases = []
        minor_releases.extend(
            Version(f"{epoch}!{major}.{minor}.{min(micros)}")
            for (
                epoch,
                major,
                minor,
            ), micros in self._epoch_major_minor_to_set_of_micro.items()
        )
        return sorted(minor_releases)

    def oldest_supported_minor_release(
        self,
        drop_months: int = 24,
        cooldown_months: int = 18,
    ) -> Version:
        """
        Get the oldest supported minor release of the package.

        Parameters
        ----------
        drop_months: int
            The expected support window for dependencies. All minor
            releases in the last ``drop_months`` will be supported.

        cooldown_months: int
            The number of months to use as a grace period for minor
            releases. The oldest supported minor release will be at
            least
        """

        if not (0 <= cooldown_months <= drop_months):
            raise ValueError("need 0 ≤ cooldown_months ≤ drop_months")

        support_window = timedelta(days=math.ceil(drop_months * DAYS_PER_MONTH))
        cooldown_period = timedelta(days=math.ceil(cooldown_months * DAYS_PER_MONTH))

        drop_date: date = self.today - support_window
        cooldown_date: date = self.today - cooldown_period

        supported_releases_before_cooldown: list[Version] = []
        releases_before_drop_date: list[Version] = []

        for release in self.minor_releases:
            release_date: date = self.release_dates[release]

            if drop_date <= release_date < cooldown_date:
                supported_releases_before_cooldown.append(release)
            elif release_date < drop_date:
                releases_before_drop_date.append(release)

        # for very new packages
        if not supported_releases_before_cooldown and not releases_before_drop_date:
            return str(min(self.releases)).removesuffix(".0").removesuffix(".0")

        return (
            str(
                min(
                    supported_releases_before_cooldown,
                    default=max(releases_before_drop_date),
                )
            )
            .removesuffix(".0")
            .removesuffix(".0")
            .removesuffix(".0")
        )


def combine_requirements(original: Requirement | str, new: Requirement | str) -> str:
    """
    Combine two version specifiers, falling back to `original` if the
    two specifiers are mutually incompatible.
    """
    parsed_original = parse_version_specifier(str(original))
    parsed_new = parse_version_specifier(str(new))
    combined = parsed_original & parsed_new
    new_specifier = str(original) if combined.is_empty() else str(combined)
    if "||" in new_specifier:
        warnings.warn("Cannot update versions with != in supported range; skipping.")
        return original
    return new_specifier.strip().removesuffix(".0").removesuffix(".0")


def _update_dependency(
    requirement: Requirement,
    drop_months: float | int,
    cooldown_months: float | int,
) -> str:
    package = Package(requirement.name)
    original_requirement = requirement.specifier
    calculated_minimum_version = package.oldest_supported_minor_release(
        drop_months=drop_months,
        cooldown_months=cooldown_months,
    )
    time_based_requirement = f">={calculated_minimum_version}"
    return combine_requirements(original_requirement, time_based_requirement)


def bump_minimum_dependencies(
    pyproject_file: str = "pyproject.toml",
    *,
    drop_months: float | int,
    cooldown_months: float | int,
) -> None:
    """..."""

    pyproject: PyProject = PyProject.load(pyproject_file)

    requirements: list[Requirement] = pyproject.project["dependencies"]
    # dependency_groups: dict[str, list] = pyproject.dependency_groups

    new_requirements = []

    for requirement in requirements:
        try:
            new = _update_dependency(
                requirement, drop_months=drop_months, cooldown_months=cooldown_months
            )
            new_requirements.append(f"{requirement.name}{new}")
        except Exception as e:
            msg = f"Unable to update package '{requirement.name}'; skipping. "
            raise RuntimeError(msg) from e

    subprocess.run(["uv", "add", "--no-sync", *new_requirements])
