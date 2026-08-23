import pytest
from pathlib import Path
from packaging.requirements import Requirement

from bump_minimum_dependencies.pyproject import PyProject


@pytest.fixture()
def simple_pyproject() -> PyProject:
    data_dir = Path(__file__).parent / "data"
    pyproject_file = data_dir / "simple_pyproject" / "pyproject.toml"
    return PyProject(pyproject_file)


def test_project_name(simple_pyproject: PyProject):
    assert simple_pyproject.project_name == "simple-pyproject"


def test_core_requirements(simple_pyproject: PyProject):
    assert simple_pyproject.core_requirements == {Requirement("numpy>=2")}


def test_optionals(simple_pyproject: PyProject):
    expected = {"optional": {Requirement("sunpy")}}
    print(simple_pyproject.optional_dependencies)
    print(expected)

    assert simple_pyproject.optional_dependencies == expected


def test_groups(simple_pyproject: PyProject):
    expected = {"group": {Requirement("plasmapy>=0.8.1")}}
    assert simple_pyproject.dependency_groups == expected


def test_dependency_group_names(simple_pyproject: PyProject):
    assert simple_pyproject.dependency_group_names == ["group"]


def test_optional_category_names(simple_pyproject: PyProject):
    assert simple_pyproject.optional_category_names == ["optional"]
