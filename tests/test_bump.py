import shutil


from bump_minimum_dependencies import bump
from bump_minimum_dependencies.inputs import Inputs
import pytest
from pathlib import Path


DEFAULT_TEST_VERBOSITY = "INFO"


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
        (
            "basic_24_21",
            "2026-01-01",
            {
                "drop_months": 24,
                "cooldown_months": 21,
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
                "no_project_table_24_21",
                "2026-08-18",
                {
                    "drop_months": 24,
                    "cooldown_months": 21,
                    "only_group": ["group"],
                    "verbosity": DEFAULT_TEST_VERBOSITY,
                },
        ),
        (
            "only_group_24_21",
            "2026-01-01",
            {
                "drop_months": 24,
                "cooldown_months": 21,
                "only_group": ["numpy"],
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "two_groups_24_21",
            "2026-01-01",
            {
                "drop_months": 24,
                "cooldown_months": 21,
                "only_group": ["astropy", "numpy"],
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "only_extra_24_21",
            "2026-01-01",
            {
                "drop_months": 24,
                "cooldown_months": 21,
                "only_extra": ["numpy"],
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "two_extras_24_21",
            "2026-01-01",
            {
                "drop_months": 24,
                "cooldown_months": 21,
                "only_extra": ["astropy", "numpy"],
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "no_extras_24_21",
            "2026-01-01",
            {
                "drop_months": 24,
                "cooldown_months": 21,
                "no_extras": True,
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "no_groups_24_12",
            "2026-01-01",
            {
                "no_groups": True,
                "drop_months": 24,
                "cooldown_months": 12,
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "skip_two_groups_12_6",
            "2026-08-18",
            {
                "drop_months": 12,
                "cooldown_months": 6,
                "no_extras": True,
                "skip_group": ["skip-this", "skip-this-too"],
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "skip_two_extras_12_6",
            "2026-08-18",
            {
                "drop_months": 12,
                "cooldown_months": 6,
                "no_groups": True,
                "skip_extra": ["skip-this", "skip-this-too"],
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "no_unnecessary_normalization_24_12",
            "2026-01-01",
            {
                "no_groups": True,
                "drop_months": 24,
                "cooldown_months": 12,
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "bump_certifi_12_6",
            "2026-08-17",
            {
                "drop_months": 12,
                "cooldown_months": 6,
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "only_package_0_0",
            "2026-08-17",
            {
                "drop_months": 0,
                "cooldown_months": 0,
                "only_group": ["update"],
                "only_extra": ["update"],
                "only_package": ["numpy"],
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "from_astropy_12_6",
            "2026-08-17",
            {
                "drop_months": 12,
                "cooldown_months": 6,
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "from_astropy_24_12",
            "2026-08-18",
            {
                "drop_months": 24,
                "cooldown_months": 12,
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "from_astropy_360_360",
            "2026-08-18",
            {
                "drop_months": 360,
                "cooldown_months": 360,
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "from_scipy_12_6",
            "2026-08-18",
            {
                "drop_months": 12,
                "cooldown_months": 6,
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "from_pydantic_12_0",
            "2026-08-18",
            {
                "drop_months": 12,
                "cooldown_months": 0,
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "from_pyright_12_0",
            "2026-08-18",
            {
                "drop_months": 12,
                "cooldown_months": 0,
                "no_groups": True,
                "no_extras": True,
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
        (
            "from_matplotlib_360_360",
            "2026-08-18",
            {
                "drop_months": 360,
                "cooldown_months": 360,
                "no_groups": True,
                "no_extras": True,
                "verbosity": DEFAULT_TEST_VERBOSITY,
            },
        ),
    ],
)
def test_bumping_minimum_requirements(
    tmp_path, monkeypatch, freezer, subdir, kwargs, date
) -> None:
    freezer.move_to(date)

    inputs = Inputs(**kwargs)

    data_dir: Path = Path(__file__).parent / "data" / subdir
    original_pyproject: Path = data_dir / "pyproject.toml"
    expected_pyproject: Path = data_dir / "pyproject.expected.toml"
    pyproject: Path = tmp_path / "pyproject.toml"

    shutil.copy(original_pyproject, pyproject)
    monkeypatch.chdir(tmp_path)

    bumper = bump.BumpMinimumDependencies(inputs=inputs)
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
def test_bumping_single_package(
    name: str, drop_months: int, cooldown_months: int, expected: str, freezer
) -> None:
    inputs = Inputs(drop_months=drop_months, cooldown_months=cooldown_months)

    freezer.move_to("2026-01-01")
    package = bump.BumpPackage(name=name, inputs=inputs)
    release = package.oldest_supported_release()
    assert str(release) == expected
