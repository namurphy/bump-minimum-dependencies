"""Contains a class to access requirement information in pyproject.toml."""

__all__ = ["PyProject"]


from pathlib import Path
import tomllib
import functools
import contextlib
from packaging.requirements import Requirement, InvalidRequirement
from typing import Any


class PyProject:
    """A class to access requirements information in pyproject.toml."""

    def __init__(self, pyproject_file: Path | str):
        self.pyproject_file = Path(pyproject_file)

        with open(self.pyproject_file, "rb") as f:
            self.pyproject = tomllib.load(f)

    @property
    def project(self) -> dict[str, Any]:
        """The project table in pyproject.toml."""
        return self.pyproject.get("project", {})

    @property
    def project_name(self) -> str | None:
        """Get project.name from pyproject.toml."""
        return self.project.get("name", None)

    @functools.cached_property
    def core_requirements(self) -> set[Requirement]:
        """
        Get project.dependencies from pyproject.toml, converting them
        into `packaging.requirements.Requirement` objects.
        """
        core_requirements = set()
        for requirement in self.project.get("dependencies", set()):
            with contextlib.suppress(InvalidRequirement, TypeError):
                core_requirements.add(Requirement(requirement))
        return core_requirements

    @functools.cached_property
    def optional_dependencies(self) -> dict[str, set[Requirement]]:
        """
        Get project.optional-dependencies from pyproject.toml, converting
        them into `packaging.requirements.Requirement` objects.
        """
        optional_dependencies: dict[str, set[Requirement]] = {}
        original_extras = self.project.get("optional-dependencies", {})
        for extra in original_extras:
            optional_dependencies[extra] = set()
            for dependency in original_extras[extra]:
                with contextlib.suppress(InvalidRequirement, TypeError):
                    optional_dependencies[extra].add(
                        Requirement(dependency),
                    )
        return optional_dependencies

    @functools.cached_property
    def optional_category_names(self) -> list[str]:
        """The category names for optional dependencies."""
        return sorted(self.optional_dependencies.keys())

    @functools.cached_property
    def dependency_group_names(self) -> list[str]:
        """The names of dependency groups."""
        return sorted(self.dependency_groups.keys())

    @functools.cached_property
    def dependency_groups(self) -> dict[str, set[Requirement]]:
        """
        Get dependency-groups from pyproject.toml, converting them into
        `packaging.requirements.Requirement` objects.
        """
        dependency_groups: dict[str, set[Requirement]] = {}
        original_groups: dict[str, list[str]] = self.pyproject.get(
            "dependency-groups", {}
        )
        for group in original_groups:
            dependency_groups[group] = set()
            for dependency in original_groups[group]:
                with contextlib.suppress(InvalidRequirement, TypeError):
                    dependency_groups[group].add(Requirement(dependency))

        return dependency_groups
