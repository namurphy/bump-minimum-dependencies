__all__ = [
    "BumpMinimumDependencies",
    "BumpPackage",
    "combine_requirements",
    "get_new_requirement_for_package",
    "logger",
    "requirement_already_included",
]

import pathlib
import requests

from dep_logic.specifiers import parse_version_specifier

import datetime

import packaging.specifiers
import packaging.version
import packaging.requirements

from packaging.requirements import Requirement

from pyproject_parser import PyProject

from . import utils

import logging

import math

import subprocess
import functools

DAYS_PER_MONTH = 30.436875


logger = logging.getLogger("bump")
logger.propagate = True
logger.setLevel(logging.WARNING)


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
        self.today = datetime.datetime.now().date()
        self.versions_to_release_dates = utils.make_version_to_release_date_dict(
            self.response,
            skip_yanked=True,
            skip_prerelease=True,
        )

    @functools.cached_property
    def response(self):
        return requests.get(
            url=f"https://pypi.org/simple/{self.name}",
            headers={"Accept": "application/vnd.pypi.simple.v1+json"},
        ).json()

    @functools.cached_property
    def releases(self) -> list[packaging.version.Version]:
        """The dates of all releases."""
        return sorted(self.versions_to_release_dates)

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
            release_date: datetime.date = self.versions_to_release_dates[release]

            if drop_date <= release_date < cooldown_date:
                supported_releases_before_cooldown.append(release)
            elif release_date < drop_date:
                releases_before_drop_date.append(release)

        # when a package's first release is during the cooldown period
        if not supported_releases_before_cooldown and not releases_before_drop_date:
            return utils.normalize_requirement_string(min(self.releases))

        return utils.normalize_requirement_string(
            min(
                supported_releases_before_cooldown,
                default=max(releases_before_drop_date),
            )
        )


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
        logger.warning("Cannot update versions with != in supported range; skipping.")
        return None

    new_specifier = utils.normalize_requirement_string(new_specifier)

    return new_specifier


def requirement_already_included(new_requirement: str, old_requirements):
    old_requirements_set: set[Requirement] = set()

    for requirement in old_requirements:
        old_requirements_set.add(Requirement(utils.normalize_requirement_string(requirement)))

    new_requirement: Requirement = Requirement(
        utils.normalize_requirement_string(new_requirement)
    )

    return new_requirement in old_requirements_set


def get_new_requirement_for_package(
    requirement: Requirement,
    drop_months: float | int,
    cooldown_months: float | int,
) -> str | None:
    """Combine the time-based requirement with the original requirement."""
    package = BumpPackage(requirement.name)
    calculated_minimum_version = package.oldest_supported_minor_release(
        drop_months=drop_months,
        cooldown_months=cooldown_months,
    )
    time_based_requirement = f">={calculated_minimum_version}"
    new_requirement = combine_requirements(
        original=requirement.specifier,
        new=time_based_requirement,
    )

    if not requirement.extras:
        return f"{requirement.name}{new_requirement}"

    return (
        f"{requirement.name}[{','.join(sorted(requirement.extras))}]{new_requirement}"
    )


class BumpMinimumDependencies:
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
        The names of the optional dependencies categories to be updated.

    group: tuple[str, ...] | list[str], keyword-only, optional
        The names of the dependency groups to be updated.

    skip_core: bool, default: False
        If `True`, skip updating core project dependencies.

    skip_package: tuple[str, ...] | list[str], keyword-only, optional
        The names of packages to skip when bumping requirements.

    Notes
    -----
    This function does not yet work when the combined requirements
    include a `!=` dependency or multiple ranges of dependencies.
    """

    def __init__(
        self,
        pyproject_file: str | pathlib.Path = "pyproject.toml",
        *,
        all_extras: bool = False,
        all_groups: bool = False,
        skip_core: bool = False,
        cooldown_months: float = 12,
        drop_months: float = 24,
        extra: tuple[str, ...] | list[str] = (),
        group: tuple[str, ...] | list[str] = (),
        skip_package: tuple[str, ...] | list[str] = (),
        only_package: tuple[str, ...] | list[str] = (),
    ):
        if cooldown_months > drop_months:
            # issue a warning when cooldown_months ≠ the default value
            if cooldown_months != 12:
                msg = f"Reducing cooldown_months to {drop_months} to equal drop_months."
                logger.warning(msg)

            cooldown_months = drop_months

        self.pyproject_file: str | pathlib.Path = pyproject_file
        self.update_all_optionals: bool = all_extras
        self.update_all_dependency_groups: bool = all_groups
        self.skip_core_requirements: bool = skip_core
        self.cooldown_months: float = cooldown_months
        self.drop_months: float = drop_months
        self.optional_categories: list[str] = [category.lower() for category in extra]
        self.dependency_groups: list[str] = [
            dependency_group.lower() for dependency_group in group
        ]
        self.packages_to_skip: list[str] = [package.lower() for package in skip_package]
        self.only_update_these_packages: list[str] = [
            package.lower() for package in only_package
        ]

        try:
            self.pyproject: PyProject = PyProject.load(pyproject_file)
        except FileNotFoundError as exc:
            exception_message = str(exc).lower()
            msg = f"Unable to load {pyproject_file} with pyproject_parser.PyProject.load()."
            if "readme" in exception_message or "license" in exception_message:
                msg += (
                    " If a readme or license file is declared in a pyproject.toml, "
                    "these files must be present alongside pyproject.toml."
                )
            raise FileNotFoundError(msg) from exc

        if isinstance(self.project_name, str):
            self.packages_to_skip.append(self.project_name)

        if not self.pyproject.project:
            raise RuntimeError("project table not defined")

        logger.info(f"Bumping minimum dependencies for {self.pyproject_file}")

    @property
    def project_name(self) -> str | None:
        """The name of the project, if available."""
        return self.pyproject.project.get("name", None)  # ty: ignore[unresolved-attribute]

    @property
    def core_requirements_to_update(self) -> list[Requirement]:
        """Core project dependencies to be updated if necessary."""
        if self.skip_core_requirements:
            return []

        try:
            all_requirements = self.pyproject.project["dependencies"]  # ty:ignore[not-subscriptable]
        except (TypeError, AttributeError, KeyError) as exc:
            errmsg = f"Unable to access dependencies in {self.pyproject_file!r}"
            raise RuntimeError(errmsg) from exc

        core_requirements_to_update: list[Requirement] = []
        for requirement in all_requirements:
            if requirement.name in self.packages_to_skip:
                continue
            if requirement.name == self.project_name:
                continue
            if (
                self.only_update_these_packages
                and requirement.name not in self.only_update_these_packages
            ):
                continue
            core_requirements_to_update.append(requirement)

        return core_requirements_to_update

    @property
    def dependency_groups_to_update(self) -> list[str]:
        """Names of dependency groups to be updated if necessary."""
        if not self.pyproject.dependency_groups:
            return []

        all_dependency_groups: list[str] = sorted(self.pyproject.dependency_groups)

        if undefined := set(self.dependency_groups) - set(all_dependency_groups):
            msg = f"the following dependency groups are not defined: {undefined}"
            raise ValueError(msg)

        if self.update_all_dependency_groups:
            return all_dependency_groups
        return self.dependency_groups

    @property
    def optional_categories_to_update(self) -> list[str]:
        """Names of categories of optional dependencies to be updated if necessary."""
        all_optionals: list[str] = sorted(
            self.pyproject.project.get("optional-dependencies", [])  # ty: ignore[unresolved-attribute]
        )
        if undefined := set(self.optional_categories) - set(all_optionals):
            raise ValueError(
                f"the following optional dependency categories are not "
                f"defined: {undefined}"
            )
        return all_optionals if self.update_all_optionals else self.optional_categories

    def get_new_requirements(
        self,
        requirements: list[Requirement],
    ) -> list[str]:
        requirements_to_update: list[Requirement] = []
        for requirement in requirements:
            if isinstance(requirement, str):
                requirement = utils.normalize_requirement_string(requirement)
                requirement = Requirement(requirement)
            if not isinstance(requirement, Requirement):
                continue
            if requirement.name.lower() in self.packages_to_skip:
                continue
            if (
                self.only_update_these_packages
                and requirement.name.lower() not in self.only_update_these_packages
            ):
                continue
            requirements_to_update.append(requirement)

        logger.debug(f"{requirements_to_update = }")

        packages_with_markers: list[str] = []
        for requirement in requirements_to_update:
            if requirement.marker:
                packages_with_markers.append(requirement.name.lower())

        new_requirements: list[str] = []
        for requirement in requirements_to_update:
            if requirement.name.lower() in packages_with_markers:
                logger.debug(str(requirement))
                continue

            try:
                new_requirement: str | None = get_new_requirement_for_package(
                    requirement=requirement,
                    drop_months=self.drop_months,
                    cooldown_months=self.cooldown_months,
                )

            # Catch any exception since if a package cannot be updated
            # for whatever reason, it should be skipped with a warning issued.
            except Exception:
                warning_message = (
                    f"Unable to update dependency {requirement}. Skipping."
                )
                logger.warning(warning_message)
            else:
                if not new_requirement:
                    continue

                if requirement_already_included(
                    new_requirement=new_requirement,
                    old_requirements=requirements_to_update,
                ):
                    continue

                new_requirements.append(f"{new_requirement}")

        return new_requirements

    def run_uv_command(
        self,
        new_requirements: list[str],
        *,
        dependency_group: str | None = None,
        extras_category: str | None = None,
    ):
        if dependency_group and extras_category:
            raise ValueError("Cannot set both dependency_group and extras_category.")

        if dependency_group:
            flag = [f"--group={dependency_group}"]
            clause = f"dependency group {dependency_group!r}"
        elif extras_category:
            flag = [f"--optional={extras_category}"]
            clause = f"optional dependencies category {extras_category}"
        else:
            flag = []
            clause = "core dependencies"

        if not new_requirements:
            msg = f"No updates to requirements for {clause}."
            logger.info(msg)
            return

        command = [
            "uv",
            "add",
            "--frozen",
            "--quiet",
            *flag,
            *new_requirements,
        ]

        msg = f"Running: {' '.join(command)}"
        logger.info(msg)
        subprocess.run(command)

    def bump_core_requirements(self) -> None:
        """Bump the core package requirements."""
        if self.skip_core_requirements:
            return

        new_requirements = self.get_new_requirements(self.core_requirements_to_update)
        self.run_uv_command(new_requirements)

    def bump_dependency_groups(self):
        """Bump requirements in dependency groups."""
        if not self.update_all_dependency_groups and not self.dependency_groups:
            return

        for dependency_group in self.dependency_groups_to_update:
            requirements = self.pyproject.dependency_groups[dependency_group]  # ty:ignore[not-subscriptable]
            new_requirements = self.get_new_requirements(requirements)  # ty:ignore[invalid-argument-type]
            self.run_uv_command(new_requirements, dependency_group=dependency_group)

    def bump_optional_dependencies(self):
        """Bump requirements in optional dependencies."""
        if not self.update_all_optionals and not self.optional_categories_to_update:
            return

        optionals = self.pyproject.project.get("optional-dependencies")  # ty:ignore[unresolved-attribute]
        if not optionals:
            logger.info("No optional dependencies found.")
            return

        for category in self.optional_categories_to_update:
            requirements = optionals[category]
            new_requirements = self.get_new_requirements(requirements)  # ty:ignore[invalid-argument-type]
            self.run_uv_command(new_requirements, extras_category=category)

    def run(self):
        """Perform all the requested and necessary updates."""
        self.bump_core_requirements()
        self.bump_dependency_groups()
        self.bump_optional_dependencies()
