import shutil


from bump_minimum_dependencies import bump
import pytest

from pathlib import Path


def get_errmsg_from_file_comparison(
    pyproject,
    expected_pyproject,
    subdir,
) -> str | None:
    with open(pyproject) as f1:
        actual = f1.readlines()

    with open(expected_pyproject) as f2:
        expected = f2.readlines()

    error_messages = []

    if len(actual) != len(expected):
        error_messages.append("Length of files do not match.")

    for line, (actual_line, expected_line) in enumerate(zip(actual, expected)):
        if actual_line != expected_line:
            actual_line = actual_line.removesuffix("\n")
            expected_line = expected_line.removesuffix("\n")
            error_messages.append(
                f"Line {line + 1}\n"
                f"  Result:   {actual_line}\n  Expected: {expected_line}\n"
            )

    if not error_messages:
        return

    expanded_comparison = (
        f"Mismatch between updated and expected pyproject.toml for {subdir = !r}.\n\n"
        + "\n".join(error_messages)
    )

    return expanded_comparison


@pytest.mark.parametrize(
    "subdir,date,kwargs",
    [
        ("trailing_dot_zero", "2026-01-01", {}),
        ("base_case", "2026-01-01", {"drop_months": 24, "cooldown_months": 21}),
        (
            "bump_all_dependency_groups",
            "2026-01-01",
            {"drop_months": 24, "cooldown_months": 21, "all_groups": True},
        ),
        (
            "bump_one_dependency_group",
            "2026-01-01",
            {"drop_months": 24, "cooldown_months": 21, "group": ["numpy"]},
        ),
        (
            "bump_two_dependency_groups",
            "2026-01-01",
            {"drop_months": 24, "cooldown_months": 21, "group": ["astropy", "numpy"]},
        ),
        (
            "astropy",
            "2026-08-17",
            {
                "drop_months": 12,
                "cooldown_months": 6,
                "all_groups": True,
                "all_extras": True,
            },
        ),
    ],
)
def test_pyproject(tmp_path, monkeypatch, freezer, subdir, kwargs, date) -> None:
    freezer.move_to(date)

    data_dir: Path = Path(__file__).parent / "data" / subdir
    original_pyproject: Path = data_dir / "pyproject.toml"
    expected_pyproject: Path = data_dir / "pyproject.expected.toml"
    pyproject: Path = tmp_path / "pyproject.toml"

    shutil.copy(original_pyproject, pyproject)
    monkeypatch.chdir(tmp_path)

    bumper = bump.BumpMinimumDependencies(**kwargs)
    bumper.run()

    if errmsg := get_errmsg_from_file_comparison(pyproject, expected_pyproject, subdir):
        pytest.fail(reason=errmsg)


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
