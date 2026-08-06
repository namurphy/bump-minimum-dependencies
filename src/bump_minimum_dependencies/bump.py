__all__ = ["BumpPackage"]


import requests

from dep_logic.specifiers import parse_version_specifier
import collections
import warnings

import datetime

import packaging.specifiers
import packaging.version
import packaging.requirements

from pyproject_parser import PyProject

import logging

import math

import subprocess
import functools


DAYS_PER_MONTH = 30.436875


def make_string_and_remove_dot_zero_suffixes(
    version: packaging.version.Version | str,
) -> str:
    """
    Convert the version into a string and remove '.0' suffixes.

    Arguments
    ---------
    version : packaging.version.Version | str
        The version to be formatted.

    Examples
    --------
    >>> import packaging
    >>> version = packaging.version.Version(version="1.5.0")
    >>> make_string_and_remove_dot_zero_suffixes(version)
    '1.5'
    >>> make_string_and_remove_dot_zero_suffixes("1.0.0")
    '1'
    """
    v = str(version).strip()
    while v.endswith(".0"):
        v = v.removesuffix(".0")
    return v


class BumpPackage:
    """
    A class used to bump minimum dependencies for a Python package.

    Parameters
    ----------
    name : str
        The name of the package.
    """

    def __init__(self, name):
        self.name = name
        self.get_release_dates()
        self.today = datetime.datetime.now().date()

    def get_release_dates(self) -> None:
        response = requests.get(
            url=f"https://pypi.org/simple/{self.name}",
            headers={"Accept": "application/vnd.pypi.simple.v1+json"},
        ).json()

        file_date = collections.defaultdict(list)
        for file in response["files"]:
            ver = file["filename"].split("-")[1]
            try:
                version = packaging.version.Version(ver)
            except packaging.version.InvalidVersion as e:
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
                    release_date = datetime.datetime.strptime(
                        file["upload-time"], format_
                    )
                except ValueError as e:
                    logging.debug(f"Invalid date: {e}")

            if not release_date:
                continue

            file_date[version].append(release_date.date())

        release_date = {version: min(file_date[version]) for version in file_date}

        self._release_dates: dict[packaging.version.Version, datetime.date] = {}
        for version, release_date in release_date.items():
            self._release_dates[version] = release_date

    @property
    def release_dates(self) -> dict[packaging.version.Version, datetime.date]:
        """A dictionary mapping the version to the date it was released."""
        return self._release_dates

    @functools.cached_property
    def releases(self) -> list[packaging.version.Version]:
        """The dates of all releases."""
        return sorted(self.release_dates)

    @functools.cached_property
    def _epoch_major_minor_to_set_of_micro(
        self,
    ) -> dict[tuple[int, int, int], set[int]]:
        """
        Dictionary to help determine the lowest micro release of each

        Each key is a tuple containing the epoch, major, and minor
        version numbers and the corresponding value is a set containing
        the micro or patch version numbers.
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
    def minor_releases(self) -> list[packaging.version.Version]:
        """The first release of each major/minor pair."""
        minor_releases: list[packaging.version.Version] = []
        minor_releases.extend(
            packaging.version.Version(f"{epoch}!{major}.{minor}.{min(micros)}")
            for (
                epoch,
                major,
                minor,
            ), micros in self._epoch_major_minor_to_set_of_micro.items()
        )
        return sorted(minor_releases)

    def oldest_supported_minor_release(
        self,
        drop_months: float = 24,
        cooldown_months: float = 18,
    ) -> str:
        """
        Get the oldest supported minor release of the package.

        Parameters
        ----------
        drop_months: float
            The expected support window for dependencies. All minor
            releases in the last ``drop_months`` will be supported.

        cooldown_months: float
            The number of months to use as a grace period for minor
            releases.  If possible, the oldest supported minor release
            will be at least `cooldown_months` old.
        """

        support_window = datetime.timedelta(
            days=math.ceil(drop_months * DAYS_PER_MONTH)
        )
        cooldown_period = datetime.timedelta(
            days=math.ceil(cooldown_months * DAYS_PER_MONTH)
        )

        drop_date: datetime.date = self.today - support_window
        cooldown_date: datetime.date = self.today - cooldown_period

        supported_releases_before_cooldown: list[packaging.version.Version] = []
        releases_before_drop_date: list[packaging.version.Version] = []

        for release in self.minor_releases:
            release_date: datetime.date = self.release_dates[release]

            if drop_date <= release_date < cooldown_date:
                supported_releases_before_cooldown.append(release)
            elif release_date < drop_date:
                releases_before_drop_date.append(release)

        # when a package's first release is during the cooldown period
        if not supported_releases_before_cooldown and not releases_before_drop_date:
            return make_string_and_remove_dot_zero_suffixes(min(self.releases))

        return make_string_and_remove_dot_zero_suffixes(
            min(
                supported_releases_before_cooldown,
                default=max(releases_before_drop_date),
            )
        )


def combine_requirements(
    original: packaging.specifiers.SpecifierSet,
    new: packaging.requirements.Requirement | str,
) -> str:
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
        return str(original)
    return new_specifier.strip().removesuffix(".0").removesuffix(".0")


def get_new_requirement_for_package(
    requirement: packaging.requirements.Requirement,
    drop_months: float | int,
    cooldown_months: float | int,
) -> str:
    package = BumpPackage(requirement.name)
    original_requirement = requirement.specifier
    calculated_minimum_version = package.oldest_supported_minor_release(
        drop_months=drop_months,
        cooldown_months=cooldown_months,
    )
    time_based_requirement = f">={calculated_minimum_version}"
    return combine_requirements(original_requirement, time_based_requirement)


def get_dependency_groups_to_update(
    *,
    group: list[str] | tuple[str, ...],
    all_groups: bool,
    pyproject: PyProject,
) -> list[str]:
    if pyproject.dependency_groups:
        all_dependency_groups: list[str] = sorted(pyproject.dependency_groups)
    else:
        all_dependency_groups: list[str] = []

    if undefined := set(group) - set(all_dependency_groups):
        raise ValueError(
            f"the following dependency groups are not defined: {undefined}"
        )

    return all_dependency_groups if all_groups else sorted(group)


def get_optional_dependencies_to_update(
    *,
    extra: list[str] | tuple[str, ...],
    all_extras: bool,
    pyproject: PyProject,
) -> list[str]:
    if pyproject.project and pyproject.project.get("optional-dependencies"):
        all_extra_categories: list[str] = sorted(
            pyproject.project["optional-dependencies"]
        )
    else:
        all_extra_categories: list[str] = []

    if undefined := set(extra) - set(all_extra_categories):
        raise ValueError(
            f"the following optional dependency categories are not defined: {undefined}"
        )

    return all_extra_categories if all_extras else sorted(extra)


def bump_minimum_dependencies(
    pyproject_file: str = "pyproject.toml",
    *,
    all_extras: bool = False,
    all_groups: bool = False,
    cooldown_months: int = 12,
    drop_months: int = 24,
    extra: tuple[str, ...] | list[str] = (),
    group: tuple[str, ...] | list[str] = (),
) -> None:
    """
    Bump the minimum core dependencies in `pyproject.toml`.

    Parameters
    ----------
    pyproject_file: str, default: "pyproject.toml"
        The path to the pyproject.toml file to be updated.

    all_extras: bool, keyword-only, default: False
        Update all optional dependencies.

    all_groups: bool, keyword-only, default: False
        Update all dependency groups.

    cooldown_months: int, keyword-only, default: 12
        The number of months since a package's release before it can
        become the minimum version, when possible.

    drop_months: int, keyword-only, default: 24
        The preferred number of months after which a minor release is
        no longer supported.

    extra: tuple[str, ...] | list[str], keyword-only, optional
        The name of the optional dependencies category to be updated.
        Not yet implemented.

    group: tuple[str, ...] | list[str], keyword-only, optional
        The name of the dependency group to be updated. Not yet
        implemented.

    Notes
    -----
    This function does not yet work when the combined requirements
    include a `!=` dependency or multiple ranges of dependencies.
    """
    if not (0 <= cooldown_months <= drop_months):
        raise ValueError("need 0 ≤ cooldown_months ≤ drop_months")

    if group and all_groups:
        raise TypeError("only one of group and all_groups can be provided.")

    if extra and all_extras:
        raise TypeError("only one of extra and all_extras can be provided.")

    pyproject: PyProject = PyProject.load(pyproject_file)
    requirements: list[packaging.requirements.Requirement] = pyproject.project[
        "dependencies"
    ]  # ty: ignore[invalid-assignment, not-subscriptable]

    dependency_groups: list[str] = get_dependency_groups_to_update(
        group=group,
        all_groups=all_groups,
        pyproject=pyproject,
    )

    optional_dependencies: list[str] = get_optional_dependencies_to_update(
        extra=extra,
        all_extras=all_extras,
        pyproject=pyproject,
    )

    new_requirements = []
    for requirement in requirements:
        try:
            new = get_new_requirement_for_package(
                requirement,
                drop_months=drop_months,
                cooldown_months=cooldown_months,
            )
            new_requirements.append(f"{requirement.name}{new}")
        except Exception:
            msg = f"Unable to update package '{requirement.name}'; skipping. "
            warnings.warn(msg)

    subprocess.run(["uv", "add", "--no-sync", *new_requirements])

    if pyproject.dependency_groups:
        for dependency_group in dependency_groups:
            new_dependency_group_requirements: list[str] = []
            for requirement in pyproject.dependency_groups[dependency_group]:
                if not isinstance(requirement, packaging.requirements.Requirement):
                    requirement = packaging.requirements.Requirement(requirement)
                try:
                    new = get_new_requirement_for_package(
                        requirement,
                        drop_months=drop_months,
                        cooldown_months=cooldown_months,
                    )
                    new_dependency_group_requirements.append(f"{requirement.name}{new}")
                except Exception:
                    msg = (
                        f"Unable to update package '{requirement.name}' for "
                        f"{dependency_group = }; skipping."
                    )
                    warnings.warn(msg)

            subprocess.run(
                [
                    "uv",
                    "add",
                    "--no-sync",
                    f"--group={dependency_group}",
                    *new_dependency_group_requirements,
                ]
            )

    if pyproject.project and pyproject.project.get("optional-dependencies"):
        for optional_dependency in optional_dependencies:
            new_extra_requirements: list[str] = []
            for requirement in pyproject.project["optional-dependencies"][
                optional_dependency
            ]:
                # requirement = packaging.requirements.Requirement(requirement)
                try:
                    new = get_new_requirement_for_package(
                        requirement,
                        drop_months=drop_months,
                        cooldown_months=cooldown_months,
                    )
                    new_extra_requirements.append(f"{requirement.name}{new}")
                except Exception:
                    msg = (
                        f"Unable to update package '{requirement.name}' for "
                        f"{extra = }; skipping."
                    )
                    warnings.warn(msg)

            subprocess.run(
                [
                    "uv",
                    "add",
                    "--no-sync",
                    f"--optional={optional_dependency}",
                    *new_extra_requirements,
                ]
            )
