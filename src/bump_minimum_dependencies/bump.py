__all__ = ["bump_minimum_dependencies"]


from packaging.requirements import Requirement
import nep29

import pyproject_parser

from dep_logic.specifiers import parse_version_specifier


def _get_oldest_allowed_version_specifier(package_name: str, n_months: int = 24) -> str:
    """
    Find the specifier (i.e., `">=1.26"`) corresponding to the oldest
    allowed dependency as per SPEC 0.
    """
    oldest_version = str(nep29.nep29_versions(package_name, n_months=n_months)[-1][0])
    while oldest_version.endswith(".0"):  # for consistency with pyproject-fmt
        oldest_version = oldest_version.removesuffix(".0")
    return f">={oldest_version}"


def _combine_specifiers(original: Requirement | str, new: Requirement | str) -> str:
    """
    Combine two version specifiers, falling back to `original` if the
    two specifiers are mutually incompatible.
    """
    parsed_original = parse_version_specifier(str(original))
    parsed_new = parse_version_specifier(str(new))
    combined = parsed_original & parsed_new
    return str(original) if combined.is_empty() else str(combined)


def _update_requirement(dep: Requirement) -> str:
    """
    Provide a requirement that combines the existing requirement along
    with new requirements.

    For example,
    Provide the new requirement (i.e., `"numpy>=1.26"`) that combines
    pre-existing requirements and
    """
    new_specifier = _get_oldest_allowed_version_specifier(dep.name)
    combined_specifier = _combine_specifiers(dep.specifier, new_specifier)
    return f"{dep.name}{combined_specifier}"


def bump_minimum_requirements() -> None:
    """
    Update the minimum allowed versions of dependencies to be consistent
    with SPEC 0.

    Scientific Python Ecosystem Coordination (SPEC) document 0
    recommends that packages support all minor releases of core
    dependencies that were made in the past 24 months, and minor
    releases of Python that were made in the past 36 months.
    """
    pyproject = pyproject_parser.PyProject.load("pyproject.toml")
    deps = pyproject.project["dependencies"]
    deps_to_update = (dep for dep in deps if dep.name not in excluded_deps)
    updated_requirements = [_update_requirement(dep) for dep in deps_to_update]
    session.run("uv", "add", "--no-sync", *updated_requirements)
