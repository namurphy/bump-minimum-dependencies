import shutil


from bump_minimum_dependencies import bump
from datetime import date
import pytest

from pathlib import Path

baseurl = "https://raw.githubusercontent.com/namurphy/bump-minimum-dependencies/refs/heads/main/tests/data/"

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
def test_bump(name, drop_months, cooldown_months, expected, freezer):
    freezer.move_to("2026-01-01")
    package = bump.Package(name=name)
    release = package.oldest_supported_minor_release(
        drop_months=drop_months, cooldown_months=cooldown_months
    )
    assert str(release) == expected


@pytest.mark.parametrize(
    "drop_months, cooldown_months", [(4, 5), (-1, 0), (0, -1)]
)
def test_drop_months_ge_cooldown_months(drop_months, cooldown_months):
    package = bump.Package(name="plasmapy")
    with pytest.raises(ValueError):
        package.oldest_supported_minor_release(
            drop_months=drop_months, cooldown_months=cooldown_months
        )


#@pytest.mark.xfail
def test_pyproject(tmp_path, monkeypatch, freezer):

    freezer.move_to("2026-01-01")

    data_dir = Path(__file__).parent / "data"
    original_pyproject = data_dir / "pyproject.toml"
    expected_pyproject = data_dir / "pyproject.expected.toml"
    pyproject = tmp_path / "pyproject.toml"

    shutil.copy(original_pyproject, pyproject)
    monkeypatch.chdir(tmp_path)

    bump.bump_minimum_dependencies(drop_months=24, cooldown_months=21)

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
            error_messages.append(f"Expected {expected_line} but got {actual_line}.")

    if msg := " ".join(error_messages):
        pytest.fail(msg)
