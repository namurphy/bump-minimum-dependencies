import warnings

import shutil


from bump_minimum_dependencies import bump
import pytest

from pathlib import Path


@pytest.mark.parametrize(
    "name, drop_months, cooldown_months, expected",
    [
        ("plasmapy", 24, 0, "2024.2"),
        ("plasmapy", 4, 0, "2025.10"),
        ("plasmapy", 4, 3, "2025.8"),
        ("plasmapy", 48, 0, "0.8.1"),
        ("plasmapy", 1, 0, "2025.10"),
        ("numpy", 24, 0, "2"),
        ("numpy", 24, 23, "1.26"),
        ("astropy", 24, 12, "6.1"),
        ("astropy", 24, 23, "6"),
        ("pyproject-fmt", 100, 100, "0.1"),
    ],
)
def test_bump(
    name: str, drop_months: int, cooldown_months: int, expected: str, freezer
) -> None:
    freezer.move_to("2026-01-01")
    package = bump.BumpPackage(name=name)
    release = package.oldest_supported_minor_release(
        drop_months=drop_months, cooldown_months=cooldown_months
    )
    assert str(release) == expected


def get_errmsg_from_file_comparison(pyproject, expected_pyproject) -> str:
    with open(pyproject) as f1:
        actual = f1.readlines()

    with open(expected_pyproject) as f2:
        expected = f2.readlines()

    error_messages = []

    if len(actual) != len(expected):
        error_messages.append("Length of files do not match.")

    for actual_line, expected_line in zip(actual, expected):
        if actual_line != expected_line:
            actual_line = actual_line.strip('" ,\n')
            expected_line = expected_line.strip('" ,\n')
            error_messages.append(
                f"Expected '{expected_line}' but got '{actual_line}'."
            )

    return " ".join(error_messages)


@pytest.mark.parametrize(
    "subdir,kwargs",
    [
        ("base_case", {"drop_months": 24, "cooldown_months": 21}),
        (
            "bump_all_dependency_groups",
            {"drop_months": 24, "cooldown_months": 21, "all_groups": True},
        ),
        (
            "bump_one_dependency_group",
            {"drop_months": 24, "cooldown_months": 21, "group": ["numpy"]},
        ),
        (
            "bump_two_dependency_groups",
            {"drop_months": 24, "cooldown_months": 21, "group": ["astropy", "numpy"]},
        ),
    ],
)
def test_pyproject(tmp_path, monkeypatch, freezer, subdir, kwargs) -> None:
    freezer.move_to("2026-01-01")

    data_dir = Path(__file__).parent / "data" / subdir
    original_pyproject = data_dir / "pyproject.toml"
    expected_pyproject = data_dir / "pyproject.expected.toml"
    pyproject = tmp_path / "pyproject.toml"

    shutil.copy(original_pyproject, pyproject)
    monkeypatch.chdir(tmp_path)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        bump.bump_minimum_dependencies(**kwargs)

    if errmsg := get_errmsg_from_file_comparison(pyproject, expected_pyproject):
        pytest.fail(reason=errmsg)


@pytest.mark.parametrize(
    "subdir,kwargs,exception",
    [
        ("base_case", {"drop_months": 12, "cooldown_months": 24}, ValueError),
        ("base_case", {"drop_months": -1, "cooldown_months": 24}, ValueError),
        ("base_case", {"drop_months": -1, "cooldown_months": -1}, ValueError),
    ],
)
def test_exceptions(tmp_path, monkeypatch, freezer, subdir, kwargs, exception) -> None:
    freezer.move_to("2026-01-01")

    data_dir = Path(__file__).parent / "data" / subdir
    original_pyproject = data_dir / "pyproject.toml"
    pyproject = tmp_path / "pyproject.toml"

    shutil.copy(original_pyproject, pyproject)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(exception):
        bump.bump_minimum_dependencies(**kwargs)
