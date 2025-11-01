__all__ = ["bump_minimum_dependencies"]

import warnings

import pyproject_parser
import requests
from packaging.requirements import Requirement

from dep_logic.specifiers import parse_version_specifier


from packaging.version import Version

from astropy.time import Time
import numpy as np

import subprocess


import functools


class Package:
    def __init__(self, name: str, url: str | None = None):
        self.name = name
        self.get_package_data(url=url)
        self.now = Time.now()

    def get_package_data(self, url: str | None = None):
        if url is None:
            url = f"https://pypi.org/pypi/{self.name}/json"
        response = requests.get(url)
        self.data = response.json()["releases"]

    @functools.cached_property
    def releases(self) -> list[Version]:
        """All releases of the package, excluding prereleases."""
        # epochs are included in the version string, e.g., "1!2025.9.0" to "2!1.0.0".
        # `Version` is able to handle these rare cases, so we do not need to do anything
        # special.  The `cabinet` package is an example on PyPI where epochs are used.

        all_releases: list[str] = sorted(self.data.keys())

        return sorted(
            [
                Version(release)
                for release in all_releases
                if not Version(release).is_prerelease
            ]
        )

    @functools.cached_property
    def release_times(self) -> dict[Version, Time]:

        def get_upload_time(release):
            time = Time(self.data[str(release)][0]["upload_time"])
            return time

        return {release: get_upload_time(release) for release in self.releases}

    @functools.cached_property
    def _epoch_major_minor_dict(self) -> dict[tuple[int, int, int], set[int]]:
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
            ), micros in self._epoch_major_minor_dict.items()
        )
        return sorted(minor_releases)

    @functools.cached_property
    def months_since_minor_release(self):
        months_ago = {}
        for release in self.minor_releases:
            release_time = self.release_times[release]
            months_ago[release] = (self.now - release_time).to_value("jd") / 30.25

        # months_ago = {
        #     release: float(
        #         (self.now - self.release_times[release]).to_value("jd") / 30.25
        #     )
        #     for release in self.minor_releases
        # }
        return months_ago

    def last_supported_release(
        self,
        months: float | int = 24,
        buffer: float | int = 3,
    ) -> str:

        if months < 0:
            raise ValueError("months must be ≥ 0")
        if not (0 <= buffer < months):
            raise ValueError("need 0 ≤ buffer < months")

        releases = list(self.months_since_minor_release.keys())
        months_since_release = np.array(list(self.months_since_minor_release.values()))

        # get index of the first minor release that occurred in the last `months` months
        index = next(
            (
                i
                for i, months_ago in enumerate(months_since_release)
                if months_ago < months
            ),
            -1,
        )

        if months_since_release[index] < buffer and index > 0:
            index -= 1

        return str(releases[index]).removesuffix(".0").removesuffix(".0")


def _combine_specifiers(original: Requirement | str, new: Requirement | str) -> str:
    """
    Combine two version specifiers, falling back to `original` if the
    two specifiers are mutually incompatible.
    """
    parsed_original = parse_version_specifier(str(original))
    parsed_new = parse_version_specifier(str(new))
    combined = parsed_original & parsed_new
    return str(original) if combined.is_empty() else str(combined)


def _update_dependency(
    requirement: Requirement, months: float | int, buffer: float | int
):
    package = Package(requirement.name)
    original_requirement = requirement.specifier
    calculated_minimum_version = package.last_supported_release(
        months=months, buffer=buffer
    )
    time_based_requirement = f">={calculated_minimum_version}"
    new_specifiers = _combine_specifiers(original_requirement, time_based_requirement)
    return new_specifiers


def bump_minimum_dependencies(
    pyproject_file: str = "pyproject.toml",
    *,
    months: float | int,
    buffer: float | int,
) -> None:
    """..."""

    pyproject: pyproject_parser.PyProject = pyproject_parser.PyProject.load(
        "pyproject.toml"
    )

    requirements: list[Requirement] = pyproject.project["dependencies"]
    dependency_groups: dict[str, list] = pyproject.dependency_groups

    new_requirements = []

    for requirement in requirements:
        try:
            new = _update_dependency(requirement, months=months, buffer=buffer)
            new_requirements.append(f"{requirement.name}{new}")
        except Exception as e:
            msg = f"Unable to update package '{requirement.name}'; skipping. "
            raise RuntimeError(msg) from e

    subprocess.run(["uv", "add", "--no-sync", *new_requirements])

# def bump_minimum_dependencies() -> None:
#    """
#    Update the minimum allowed versions of dependencies to be consistent
#    with SPEC 0.
#
#    Scientific Python Ecosystem Coordination (SPEC) document 0
#    recommends that packages support all minor releases of core
#    dependencies that were made in the past 24 months, and minor
#    releases of Python that were made in the past 36 months.
#    """
#    excluded_deps = {}
#
#    pyproject = pyproject_parser.PyProject.load("pyproject.toml")
#    deps = pyproject.project["dependencies"]
#    deps_to_update = (dep for dep in deps if dep.name not in excluded_deps)
#    updated_requirements = [_update_requirement(dep) for dep in deps_to_update]
#    #    session.run("uv", "add", "--no-sync", *updated_requirements)
#
#    subprocess.run(
#        ["uv", "add", "--no-sync"],
#        *updated_requirements,
#        capture_output=True,
#        text=True,
#        check=True,
#    )
#
