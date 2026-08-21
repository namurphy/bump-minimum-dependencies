import datetime
import packaging.version
import packaging.requirements

import pytest
from bump_minimum_dependencies import utils


import requests


@pytest.mark.parametrize(
    "input,expected",
    [
        ("ASTROPY>=3.0.0.0.0", "astropy>=3"),
        ("PyYAML>4.0.0,<5.0.0", "pyyaml>4,<5"),
        (packaging.version.Version("0.1.0"), "0.1"),
        (packaging.requirements.Requirement("a<0.6.0,>=0.3.0"), "a<0.6,>=0.3"),
    ],
)
def test_normalize_requirement_string(input, expected):
    result = utils.normalize_requirement_string(input)
    assert result == expected


@pytest.mark.parametrize(
    "filename,package,version",
    [
        ("plasmapy-0.3.0.tar.gz", "plasmapy", "0.3.0"),
        (
            "bump_minimum_dependencies-0.1.1-py3-none-any.whl",
            "bump-minimum-dependencies",
            "0.1.1",
        ),
        (
            "bump_minimum_dependencies-0.1.1.tar.gz",
            "bump_minimum_dependencies",
            "0.1.1",
        ),
        ("pytz-2026.1.post1-py2.py3-none-any.whl", "pytz", "2026.1.post1"),
        ("pytz-2015.6-py2.py3-none-any.whl", "pytz", "2015.6"),
        ("pytz-2015.6.tar.bz2", "pytz", "2015.6"),
        ("pytz-2015.6.tar.gz", "pytz", "2015.6"),
        ("pytz-2015.6.zip", "pytz", "2015.6"),
        ("astropy-1.0.3-cp26-none-win32.whl", "astropy", "1.0.3"),
        ("astropy-1.1.post1.tar.gz", "astropy", "1.1.post1"),
        ("astropy-1.3-cp27-cp27m-manylinux1_x86_64.whl", "astropy", "1.3"),
        (
            "astropy-1.0.1-cp27-none-macosx_10_6_intel.macosx_10_9_intel.macosx_10_9_x86_64.macosx_10_10_intel.macosx_10_10_x86_64.whl",
            "astropy",
            "1.0.1",
        ),
        ("numpy-1.6.1.zip", "numpy", "1.6.1"),
        ("numpy-1.7.2.tar.gz", "numpy", "1.7.2"),
        ("numpy-1.10.0.post2.tar.gz", "numpy", "1.10.0.post2"),
        ("pip-8.1.1-py2.py3-none-any.whl", "pip", "8.1.1"),
        ("pip-26.1.2-py3-none-any.whl", "pip", "26.1.2"),
        ("numba-0.49.1rc1.tar.gz", "numba", "0.49.1rc1"),
        ("certifi-2025.10.5.tar.gz", "certifi", "2025.10.5"),
    ],
)
def test_version_from_pypi_filename(filename: str, package: str, version: str):
    result = utils.version_from_pypi_filename(filename, package)
    expected = packaging.version.Version(version)
    assert result == expected


prerelease = packaging.version.Version("0.1.0b2")
v010 = packaging.version.Version("0.1.0")
v011 = packaging.version.Version("0.1.1")
yanked_release = packaging.version.Version("0.2.0")


def test_make_version_to_release_date_dict_skip():
    package = "bump-minimum-dependencies"

    response = requests.get(
        url=f"https://pypi.org/simple/{package}",
        headers={"Accept": "application/vnd.pypi.simple.v1+json"},
    ).json()

    result = utils.make_version_to_release_date_dict(
        response,
        skip_prerelease=True,
        skip_yanked=True,
    )

    assert v010 in result
    assert v011 in result
    assert result[v010] == datetime.date(2026, 8, 19)
    assert result[v011] == datetime.date(2026, 8, 19)
    assert prerelease not in result
    assert yanked_release not in result


def test_make_version_to_release_date_dict_keep():
    package = "bump-minimum-dependencies"

    response = requests.get(
        url=f"https://pypi.org/simple/{package}",
        headers={"Accept": "application/vnd.pypi.simple.v1+json"},
    ).json()

    result = utils.make_version_to_release_date_dict(
        response,
        skip_prerelease=False,
        skip_yanked=False,
    )
    assert prerelease in result
    assert yanked_release in result
    assert result[prerelease] == datetime.date(2026, 8, 8)
    assert result[yanked_release] == datetime.date(2026, 8, 20)


def test_make_version_to_release_date_dict_certifi():
    package = "certifi"
    response = requests.get(
        url=f"https://pypi.org/simple/{package}",
        headers={"Accept": "application/vnd.pypi.simple.v1+json"},
    ).json()

    result = utils.make_version_to_release_date_dict(
        response,
        skip_prerelease=True,
        skip_yanked=True,
    )
    ver = packaging.version.Version("2025.10.5")
    assert ver in result
