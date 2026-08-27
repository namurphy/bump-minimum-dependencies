"""Core functionality for bumping dependencies."""

__all__ = [
    "BumpMinimumDependencies",
    "BumpSinglePackage",
    "combine_requirements",
    "get_new_requirement_for_package",
    "requirement_already_included",
]

import pathlib

import click
import requests

from dep_logic.specifiers import parse_version_specifier

import datetime

import packaging.specifiers
from packaging.version import Version
import packaging.requirements

from packaging.requirements import Requirement


from bump_minimum_dependencies.pyproject import PyProject
from bump_minimum_dependencies.logging import logger, package_prefix, log_uv_command
from bump_minimum_dependencies import utils
from bump_minimum_dependencies.inputs import Inputs


import subprocess
import functools


class NoReleasesError(Exception):
    """When no releases of a package can be identified."""


class BumpSinglePackage:
    """
    A class used to bump minimum dependencies for a Python package.

    Parameters
    ----------
    name : str
        The name of the package.

    inputs : bump_minimum_dependencies.inputs.Inputs
    """

    def __init__(self, name: str, inputs: Inputs):
        self.name = name
        self.today: datetime.date = datetime.datetime.now().date()
        self.versions_to_release_dates: dict[Version, datetime.date] = (
            utils.make_version_to_release_date_dict(
                response=self.response_from_pypi,
                skip_yanked=True,
                skip_prerelease=True,
            )
        )
        self.inputs = inputs

    @property
    def prefix(self) -> str:
        """The package prefix for log messages."""
        return package_prefix(self.name)

    @functools.cached_property
    def response_from_pypi(self) -> dict:
        """Representation of JSON file from PyPI."""
        return requests.get(
            url=f"https://pypi.org/simple/{self.name}",
            headers={"Accept": "application/vnd.pypi.simple.v1+json"},
        ).json()

    @functools.cached_property
    def released_versions(self) -> list[Version]:
        """The versions of all releases."""
        return sorted(self.versions_to_release_dates)

    @functools.cached_property
    def _epoch_major_minor_to_set_of_micro(
        self,
    ) -> dict[tuple[int, int, int], set[int]]:
        """
        Dictionary to help determine the lowest micro release of each
        major minor pair.

        Each key is a tuple containing the epoch, major, and minor
        version numbers and the corresponding value is a set containing
        the micro or patch version numbers.
        """
        epoch_major_minor_to_set_of_micro = {}

        for version in self.released_versions:
            epoch = version.epoch
            major = version.major
            minor = version.minor
            micro = version.micro

            if (epoch, major, minor) not in epoch_major_minor_to_set_of_micro:
                if version.post is not None:
                    logger.info(
                        f"{self.prefix} Skipping post release: {str(version)}",
                    )
                    continue
                epoch_major_minor_to_set_of_micro[(epoch, major, minor)] = {micro}
            else:
                epoch_major_minor_to_set_of_micro[(epoch, major, minor)] |= {micro}

        return epoch_major_minor_to_set_of_micro

    @functools.cached_property
    def minor_releases(self) -> list[Version]:
        """The first release of each major/minor pair."""
        minor_releases: list[Version] = []

        for (
            epoch,
            major,
            minor,
        ), micros in self._epoch_major_minor_to_set_of_micro.items():
            version_str = f"{epoch}!{major}.{minor}.{min(micros)}"
            version = Version(version_str)
            if version in self.released_versions:
                minor_releases.append(version)
            else:
                logger.debug(
                    f"{self.prefix} Reconstructed version {version} not found "
                    f"in released versions. Skipping.",
                )

        return sorted(minor_releases)

    @functools.cached_property
    def last_release_before_drop_date(self) -> Version:
        releases_before_drop_date: list[Version] = [
            version
            for version, release_date in self.versions_to_release_dates.items()
            if release_date <= self.inputs.drop_date
        ]

        return max(releases_before_drop_date, default=Version("0"))

    def adjust_micro(self, minimum_minor_version: Version) -> Version:
        """
        Drop older micro releases when the major/minor release numbers
        are too low, in particular when there have been a large number
        of micro releases.
        """
        minimum_micro_version: Version = self.last_release_before_drop_date

        if minimum_minor_version >= minimum_micro_version:
            return minimum_minor_version

        def log_switch(minor_version, micro_version, reason):
            minor_date = self.versions_to_release_dates[minor_version].isoformat()
            micro_date = self.versions_to_release_dates[micro_version].isoformat()
            logger.warning(
                f"{self.prefix} Bumping version from "
                f"{str(minor_version)} ({minor_date}) to "
                f"{str(micro_version)} ({micro_date}) {reason}."
            )

        if minimum_micro_version.micro >= 25:
            log_switch(
                minor_version=minimum_minor_version,
                micro_version=minimum_micro_version,
                reason="because of large number of micro releases",
            )
            return minimum_micro_version

        if minimum_minor_version.major >= 1 or minimum_minor_version.epoch > 0:
            return minimum_minor_version

        if minimum_minor_version.major < 1:
            log_switch(
                minor_version=minimum_minor_version,
                micro_version=minimum_micro_version,
                reason="due to pre-1.0 release number",
            )
            return minimum_micro_version

        return minimum_minor_version

    def oldest_supported_release(self) -> str:
        """Get the oldest supported release of the package."""

        if not self.minor_releases:
            msg = f"[{self.name}] No minor releases identified."
            raise NoReleasesError(msg)

        supported_minor_releases_before_cooldown: list[Version] = []
        minor_releases_before_drop_date: list[Version] = []

        for minor_release in self.minor_releases:
            try:
                release_date: datetime.date = self.versions_to_release_dates[
                    minor_release
                ]
            except KeyError:
                logger.debug(
                    f"{self.prefix} Version {str(minor_release)} "
                    f"is not in the mapping from versions to release "
                    f"dates, possibly due to non-standard versioning or "
                    f"that the release was yanked or a prerelease. "
                    f"Continuing.",
                )
                continue

            if self.inputs.drop_date <= release_date < self.inputs.cooldown_date:
                supported_minor_releases_before_cooldown.append(minor_release)
            elif release_date < self.inputs.drop_date:
                minor_releases_before_drop_date.append(minor_release)

        if not supported_minor_releases_before_cooldown:
            logger.debug(
                f"{self.prefix} "
                f"No supported releases prior to cooldown. "
                f"({self.inputs.cooldown_date.isoformat()})",
            )

        if not minor_releases_before_drop_date:
            logger.debug(
                f"{self.prefix} "
                f"No releases prior to drop date "
                f"({self.inputs.drop_date.isoformat()}).",
            )

        # when a package's first release is during the cooldown period
        if (
            not supported_minor_releases_before_cooldown
            and not minor_releases_before_drop_date
        ):
            logger.debug(
                f"{self.prefix} First release is during the cooldown period.",
            )
            return utils.normalize_requirement_string(min(self.released_versions))

        new_minimum_version: Version = min(
            supported_minor_releases_before_cooldown,
            default=max(
                minor_releases_before_drop_date,
                default=min(self.minor_releases),
            ),
        )

        new_minimum_version: Version = self.adjust_micro(new_minimum_version)

        new_minimum_version_release_date: datetime.date = (
            self.versions_to_release_dates[new_minimum_version]
        )

        logger.info(
            f"{self.prefix} "
            f"New minimum version: {str(new_minimum_version)} "
            f"({new_minimum_version_release_date.isoformat()})",
        )

        return utils.normalize_requirement_string(new_minimum_version)


def combine_requirements(
    original: packaging.specifiers.SpecifierSet,
    new: str,
) -> str | None:
    """
    Combine two version specifiers, falling back to `original` if the
    two specifiers are mutually incompatible.
    """
    parsed_original = parse_version_specifier(str(original))
    parsed_new = parse_version_specifier(str(new))
    if parsed_new == parsed_original:
        return str(original)
    combined = parsed_original & parsed_new
    new_specifier = str(original) if combined.is_empty() else str(combined)
    if "||" in new_specifier:
        logger.warning(
            "Cannot update versions with multiple != in supported range. Skipping.",
        )
        return None

    new_specifier = utils.normalize_requirement_string(new_specifier)

    return new_specifier


def requirement_already_included(new_requirement: str, old_requirements):
    old_requirements_set: set[Requirement] = set()

    for requirement in old_requirements:
        old_requirements_set.add(
            Requirement(utils.normalize_requirement_string(requirement))
        )

    new_requirement: Requirement = Requirement(
        utils.normalize_requirement_string(new_requirement)
    )

    return new_requirement in old_requirements_set


def get_new_requirement_for_package(
    requirement: Requirement, inputs: Inputs
) -> str | None:
    """Combine the time-based requirement with the original requirement."""
    package = BumpSinglePackage(requirement.name, inputs=inputs)
    logger.debug(
        f"{package_prefix(requirement.name)} Original specifier: {str(requirement.specifier)}",
    )
    calculated_minimum_version = package.oldest_supported_release()
    time_based_requirement = f">={calculated_minimum_version}"
    logger.debug(
        f"{package_prefix(requirement.name)} Time-based specifier: {time_based_requirement}",
    )
    combined_requirement = combine_requirements(
        original=requirement.specifier,
        new=time_based_requirement,
    )

    if requirement.extras:
        new_requirement = f"{requirement.name}[{','.join(sorted(requirement.extras))}]{combined_requirement}"
    else:
        new_requirement = f"{requirement.name}{combined_requirement}"

    logger.info(
        f"{package_prefix(requirement.name)} Combined requirement: {new_requirement}",
    )

    return new_requirement


class BumpMinimumDependencies:
    """
    Bump the minimum core dependencies in `pyproject.toml`.

    Parameters
    ----------
    inputs : bump_minimum_dependencies.inputs.Inputs
        Representation of the inputs provided to the CLI tool.

    Notes
    -----
    This function does not yet work when the combined requirements
    include a `!=` dependency or multiple ranges of dependencies.
    """

    def __init__(self, inputs: Inputs = Inputs()):
        logger.setLevel(inputs.verbosity)

        self.pyproject_file: str | pathlib.Path = inputs.pyproject_file

        self.inputs: Inputs = inputs

        try:
            self.pyproject: PyProject = PyProject(inputs.pyproject_file)
        except FileNotFoundError as exc:
            msg = f"Cannot load {inputs.pyproject_file}. Stopping."
            raise click.ClickException(msg) from exc

        if isinstance(self.project_name, str):
            self.inputs.packages_to_skip.add(self.project_name)

        logger.info(
            msg=f"Bumping minimum dependencies for {inputs.pyproject_file.resolve()}",
            extra={"markup": True},
        )

    @property
    def project_name(self) -> str | None:
        """The name of the project, if available."""
        return self.pyproject.project_name

    @property
    def project_dependencies_to_update(self) -> set[Requirement]:
        """Core project dependencies to be updated if necessary."""
        if self.inputs.skip_project_dependencies:
            return set()

        try:
            all_requirements = self.pyproject.core_requirements
        except (TypeError, AttributeError, KeyError):
            msg = (
                f"project.dependencies not found in "
                f"{self.pyproject_file!r}; no updates to core project"
                f"dependencies made."
            )
            logger.warning(msg, extra={"markup": True})
            all_requirements = set()

        core_requirements_to_update: set[Requirement] = set()
        for requirement in all_requirements:
            if requirement.name in self.inputs.packages_to_skip:
                continue

            if requirement.name == self.project_name:
                continue

            if (
                self.inputs.packages_to_update
                and requirement.name not in self.inputs.packages_to_update
            ):
                continue
            core_requirements_to_update.add(requirement)

        return core_requirements_to_update

    @property
    def groups_to_update(self) -> list[str]:
        """Names of dependency groups to be updated if necessary."""
        if not self.pyproject.dependency_groups:
            return []

        all_groups: set[str] = set(self.pyproject.dependency_group_names)

        if undefined := self.inputs.groups_to_update - all_groups:
            raise click.ClickException(
                f"The following dependency groups are undefined: {', '.join(undefined)}"
            )

        if duplicated := self.inputs.groups_to_update & self.inputs.groups_to_skip:
            raise click.ClickException(
                f"The following dependency groups cannot be provided "
                f"to both --group and --skip-group: {', '.join(duplicated)}"
            )

        if self.inputs.update_all_groups:
            groups_to_update = sorted(all_groups - self.inputs.groups_to_skip)
        else:
            groups_to_update = sorted(self.inputs.groups_to_update)

        logger.warning(f"Dependency groups to update: {', '.join(groups_to_update)}")

        return groups_to_update

    @property
    def extras_to_update(self) -> list[str]:
        """Names of categories of optional dependencies to be updated if necessary."""
        all_extras: set[str] = set(self.pyproject.optional_category_names)
        if undefined := self.inputs.extras_to_update - all_extras:
            raise click.ClickException(
                f"The following extras are not defined: {', '.join(undefined)}"
            )

        if duplicated := self.inputs.extras_to_update & self.inputs.extras_to_skip:
            raise click.ClickException(
                "The following extras cannot be provided to both "
                f"--extra and --skip-extra: {', '.join(duplicated)}"
            )

        if self.inputs.update_all_extras:
            extras_to_update = sorted(all_extras - self.inputs.extras_to_skip)
        else:
            extras_to_update = sorted(self.inputs.extras_to_update)

        logger.info(f"Extras to update: {', '.join(extras_to_update)}")
        return extras_to_update

    def get_new_requirements(
        self,
        requirements: set[Requirement],
        inputs: Inputs,
    ) -> list[str]:
        dependencies_to_update: list[Requirement] = []
        for requirement in requirements:
            if requirement.name.lower() in self.inputs.packages_to_skip:
                continue

            if (
                self.inputs.packages_to_update
                and requirement.name.lower() not in self.inputs.packages_to_update
            ):
                continue

            dependencies_to_update.append(requirement)

        if dependencies_to_update:
            logger.debug(
                "Requirements to update: "
                f"{', '.join([str(requirement) for requirement in dependencies_to_update])}",
            )

        packages_with_markers: list[str] = []
        for requirement in dependencies_to_update:
            if requirement.marker:
                packages_with_markers.append(requirement.name.lower())

        new_requirements: list[str] = []
        for requirement in dependencies_to_update:
            if requirement.name.lower() in packages_with_markers:
                logger.debug(str(requirement), extra={"markup": True})
                continue

            try:
                new_requirement: str | None = get_new_requirement_for_package(
                    requirement=requirement,
                    inputs=inputs,
                )
            except NoReleasesError:
                logger.warning(
                    f"{package_prefix(requirement.name)} No releases identified from PyPI. Skipping.",
                )
            except requests.exceptions.JSONDecodeError:
                logger.warning(
                    f"{package_prefix(requirement.name)} Cannot decode JSON metadata from "
                    f"PyPI. Skipping.",
                )
            # Catch all other exceptions since if a package cannot be updated
            # for whatever reason, it should be skipped with a warning issued.
            except Exception as exc_info:
                warning_message = (
                    f"{package_prefix(requirement.name)} Unable to update requirement. Skipping.",
                )
                logger.warning(
                    warning_message, exc_info=exc_info, extra={"markup": True}
                )
            else:
                if not new_requirement:
                    continue

                if requirement_already_included(
                    new_requirement=new_requirement,
                    old_requirements=dependencies_to_update,
                ):
                    continue

                new_requirements.append(f"{new_requirement}")

        return new_requirements

    def run_uv_commands(
        self,
        new_requirements: list[str],
        *,
        group: str | None = None,
        extra: str | None = None,
    ) -> None:
        if group and extra:
            raise ValueError("Cannot set both dependency_group and extras_category.")

        if group:
            flag = [f"--group={group}"]
            clause = f"dependency group {group!r}"
        elif extra:
            flag = [f"--extra={extra}"]
            clause = f"optional dependencies category {extra!r}"
        else:
            flag = []
            clause = "project dependencies"

        if not new_requirements:
            logger.info(
                f"No updates for for {clause}.", extra={"markup": True}
            )
            return

        for new_requirement in new_requirements:
            # Run a separate `uv add` command for each requirement
            # so that the other updates will be performed.
            command = [
                "uv",
                "add",
                "--frozen",
                "--quiet",
                *flag,
                new_requirement,
            ]

            command_string = " ".join(command)
            log_uv_command(command)

            try:
                subprocess.run(command, check=True, capture_output=True)
            except subprocess.CalledProcessError as exc_info:
                logger.error(
                    f"Command failed: {command_string}",
                    exc_info=exc_info,
                )
                logger.warning(
                    f"Update not performed: {new_requirement}. Continuing.",
                )

    def bump_project_dependencies(self) -> None:
        """Bump requirements in project.dependencies."""
        new_requirements: list[str] = self.get_new_requirements(
            requirements=self.project_dependencies_to_update,
            inputs=self.inputs,
        )
        self.run_uv_commands(new_requirements)

    def bump_groups(self) -> None:
        """Bump requirements in dependency groups."""

        msg = (
            "No dependency groups to update."
            if not self.groups_to_update
            else f"Dependency groups to update: {', '.join(self.groups_to_update)}."
        )

        logger.info(msg)

        for group in self.groups_to_update:
            requirements: set[Requirement] = self.pyproject.dependency_groups[group]
            new_requirements: list[str] = self.get_new_requirements(
                requirements=requirements,
                inputs=self.inputs,
            )
            self.run_uv_commands(new_requirements, group=group)

    def bump_extras(self) -> None:
        """Bump requirements in optional dependencies (extras)."""
        for category in self.extras_to_update:
            requirements: set[Requirement] = self.pyproject.optional_dependencies[
                category
            ]
            new_requirements: list[str] = self.get_new_requirements(
                requirements=requirements,
                inputs=self.inputs,
            )
            self.run_uv_commands(new_requirements, extra=category)

    def run(self) -> None:
        """Perform all the requested and necessary updates."""
        self.bump_project_dependencies()
        self.bump_groups()
        self.bump_extras()
