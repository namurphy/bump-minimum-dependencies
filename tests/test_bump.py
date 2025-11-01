import shutil

from bump_minimum_dependencies import bump
from astropy.time import Time
import pytest
import filecmp

from pathlib import Path

baseurl = "https://raw.githubusercontent.com/namurphy/bump-minimum-dependencies/refs/heads/main/tests/data/"

start_of_2026 = Time("2026-01-01 00:00:01.000000")

@pytest.fixture(scope="module")
def plasmapy():
    name = "plasmapy"
    instance = bump.Package(
        name=name,
        url=f"{baseurl}{name}.json",
    )
    instance.now = start_of_2026
    return instance



#@pytest.mark.parametrize("package", ["plasmapy"], indirect=True)
@pytest.mark.parametrize(
    "months_buffer_expected",
    [
        (24, 0, "2024.2"),
        (4, 0, "2025.10"),
        (4, 3, "2025.8"),
        (48, 0, "0.8.1"),
        (1, 0, "2025.10"),
    ]
)
def test_package(plasmapy, months_buffer_expected):
    months, buffer, expected = months_buffer_expected
    release = plasmapy.last_supported_release(months=months, buffer=buffer)
    assert str(release) == expected


@pytest.mark.parametrize("months, buffer", [(4, 5), (4, 4), (-1, 0), (0, -1)])
def test_months_exceeds_buffer(plasmapy, months, buffer):
    with pytest.raises(ValueError):
        plasmapy.last_supported_release(months=months, buffer=buffer)


def test_pyproject(plasmapy, tmp_path, monkeypatch):
    data_dir = Path(__file__).parent / "data"
    original_pyproject = data_dir / "pyproject.toml"
    expected_pyproject = data_dir / "pyproject.expected.toml"
    pyproject = tmp_path / "pyproject.toml"

    shutil.copy(original_pyproject, pyproject)
    monkeypatch.chdir(tmp_path)

    bump.bump_minimum_dependencies(months=24, buffer=6)

#    if filecmp.cmp(pyproject, expected_pyproject, shallow=False):
#        return

    with open(pyproject) as f1:
        actual = f1.readlines()

    with open(expected_pyproject) as f2:
        expected = f2.readlines()

    error_messages = []

    for actual_line, expected_line in zip(actual, expected):
        if actual_line != expected_line:
            actual_line = actual_line.strip(""" '", \n""")
            expected_line = expected_line.strip(""" '", \n""")
            error_messages.append(f"Expected {expected_line}, but got {actual_line}. ")

    if msg := "\n".join(error_messages):
        pytest.fail(msg)