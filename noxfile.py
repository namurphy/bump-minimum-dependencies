# /// script
# python_version = ">=3.13"
# dependencies = [
#     "nox",
#     "nox-uv",
#     "requests",
#     "tomli_w",
#     "distlib==0.4.3",
# ]
# ///

import difflib
import filecmp
import shutil
import tomllib
import warnings


import nox
import nox_uv
from pathlib import Path


import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

import tomli_w

nox.options.default_venv_backend = "uv"

_HERE = Path(__file__).parent

supported_python_versions: tuple[str, ...] = ("3.13", "3.14")
maxpython: str = sorted(supported_python_versions)[-1]


@nox_uv.session(python=maxpython, uv_groups=["dev"])
def lint(session: nox.Session) -> None:
    """Run prek on all files."""
    session.run(
        "prek",
        "run",
        "--all-files",
        "--quiet",
        *session.posargs,
    )


@nox_uv.session(python=supported_python_versions, uv_groups=["dev"])
def test(session: nox.Session) -> None:
    """Run tests."""
    session.run(
        "pytest",
        ".",
        "--tb=short",
        "--doctest-modules",
        "--doctest-continue-on-failure",
        *session.posargs,
    )


@nox_uv.session(python=maxpython, uv_groups=["dev"])
def ty(session: nox.Session) -> None:
    """Perform static type checking with ty."""
    args = session.posargs or ["--fix"]
    session.run("ty", "check", ".", *args)


@nox.session(python=supported_python_versions)
def build(session: nox.Session) -> None:
    """Build the package."""
    session.run("uv", "build", "--verbose", *session.posargs)


@nox.session(python=supported_python_versions)
def run(session: nox.Session) -> None:
    """Run the package."""
    session.install(".")
    session.run("bump-minimum-dependencies", *session.posargs)


@nox.session(python=supported_python_versions)
def test_cli(session: nox.Session) -> None:
    """Test the command line interface."""
    session.install(".")

    session.run_install("bump-minimum-dependencies", "--version")
    session.run_install("faketime", "--version", external=True)

    tmp_dir = Path(session.create_tmp())
    source_dir = Path("tests/data/base_case")
    target_dir = tmp_dir / "base_case"
    shutil.copytree(source_dir, target_dir)
    session.chdir(target_dir)

    bump_command = [
        "bump-minimum-dependencies",
        "--drop-months=24",
        "--cooldown-months=21",
    ]

    session.run(
        "faketime",
        "2026-01-01",
        *bump_command,
        external=True,
    )

    result = Path("pyproject.toml").read_text().splitlines(keepends=True)
    expected = Path("pyproject.expected.toml").read_text().splitlines(keepends=True)

    if filecmp.cmp("pyproject.toml", "pyproject.expected.toml", shallow=False):
        return

    diff = list(
        difflib.unified_diff(
            result, expected, fromfile=str(result), tofile=str(expected)
        )
    )

    for x in diff[2:]:
        print(x.removesuffix("\n"))

    session.error(
        "The resulting pyproject.toml does not match pyproject.expected.toml."
    )


def _get_retry_session(
    retries: int = 3, backoff_factor: float = 1.0
) -> requests.Session:
    """Create a requests Session configured with exponential backoff retries."""
    session = requests.Session()
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _download_pyproject(
    repo_slug: str,
    session: requests.Session | None = None,
) -> list[Path]:
    """Download the `pyproject.toml` file from a GitHub repository.

    Parameters
    ----------
    repo_slug : str
        The GitHub repository target formatted as "OWNER/REPO".
    session : requests.Session, optional
        A session with pre-configured retry behavior.

    Returns
    -------
    list of Path
        Paths to the downloaded local files, or an empty list if not found.
    """
    file_name = "pyproject.toml"
    # Direct raw endpoint bypasses API overhead and rate limits
    raw_url = f"https://raw.githubusercontent.com/{repo_slug}/HEAD/{file_name}"
    headers = {"User-Agent": "Python-GH-File-Fetcher"}

    http = session or _get_retry_session()

    try:
        # Tuple timeout: (connect_timeout, read_timeout)
        response = http.get(raw_url, headers=headers, timeout=(5, 30))
    except requests.RequestException as exc:
        warnings.warn(
            f"Network error downloading '{file_name}' from '{repo_slug}': {exc}",
            UserWarning,
            stacklevel=2,
        )
        return []

    if response.status_code == 404:
        warnings.warn(
            f"'{file_name}' not found in repository '{repo_slug}'. Skipping download.",
            UserWarning,
            stacklevel=2,
        )
        return []

    if not response.ok:
        warnings.warn(
            f"HTTP {response.status_code} downloading '{file_name}' from '{repo_slug}'. Skipping.",
            UserWarning,
            stacklevel=2,
        )
        return []

    repo_name = repo_slug.split("/")[1]
    output_path = Path("example_pyprojects") / repo_name
    output_path.mkdir(parents=True, exist_ok=True)

    dest_file = output_path / file_name
    dest_file.write_bytes(response.content)

    return [dest_file]


def _clean_pyproject_files(root_dir: str | Path = "example_pyprojects") -> list[Path]:
    """
    Recursively find pyproject.toml files in subdirectories and remove
    `project.license-files`, `project.readme`, `project.license.file`,
    and `project.authors` fields.

    Parameters
    ----------
    root_dir : str or Path, default="."
        The root directory to search from.

    Returns
    -------
    list of Path
        List of paths to files that were modified.
    """
    root_path = Path(root_dir).resolve()
    modified_files: list[Path] = []

    for file_path in root_path.rglob("pyproject.toml"):
        if file_path.parent == root_path:
            continue

        with file_path.open("rb") as f:
            data = tomllib.load(f)

        project_table = data.get("project")
        if not isinstance(project_table, dict):
            continue

        modified = False

        # Remove top-level project keys
        for key in ("license-files", "readme", "authors"):
            if key in project_table:
                project_table.pop(key)
                modified = True

        # Remove project.license.file if project.license is a dict/table
        license_table = project_table.get("license")
        if isinstance(license_table, dict) and "file" in license_table:
            license_table.pop("file")
            modified = True

            # Clean up project.license table if it is now empty
            if not license_table:
                project_table.pop("license")

        if not modified:
            continue

        with file_path.open("wb") as f:
            tomli_w.dump(data, f)

        modified_files.append(file_path)

    return modified_files


def _copy_pyproject_files(
    target_name: str = "pyproject.original.toml",
    root_dir: str | Path = "example_pyprojects",
) -> list[Path]:
    """Recursively search subdirectories for `pyproject.toml` and copy

    each to `target_name` within the same directory.

    Parameters
    ----------
    target_name : str
        The destination filename (e.g., "pyproject.original.toml" or
        "pyproject.result.toml").
    root_dir : str or Path, default="."
        The root directory to search from.

    Returns
    -------
    list of Path
        Paths to the newly created target files.
    """
    root_path = Path(root_dir).resolve()
    created_files: list[Path] = []

    for src_path in root_path.rglob("pyproject.toml"):
        # Skip pyproject.toml in the root directory itself
        if src_path.parent == root_path:
            continue

        dest_path = src_path.with_name(target_name)
        shutil.copy2(src_path, dest_path)
        created_files.append(dest_path)

    return created_files


@nox.session()
def download_pyprojects(session: nox.Session) -> None:
    repositories = [
        "apache/airflow",
        "astropy/astropy",
        "django/django",
        "fastapi/fastapi",
        "home-assistant/core",
        "indygreg/python-build-standalone",
        "matplotlib/matplotlib",
        "pallets/flask",
        "pandas-dev/pandas",
        "PlasmaPy/PlasmaPy",
        "pydantic/pydantic",
        "pytest-dev/pytest",
        "python-poetry/poetry",
        "pytorch/pytorch",
        "pyvista/pyvista",
        "scikit-image/scikit-image",
        "scikit-learn/scikit-learn",
        "scipy/scipy",
        "sqlalchemy/sqlalchemy",  # failed to parse pyproject.toml
        "sunpy/sunpy",
        "yt-project/yt",
    ]

    for repository in repositories:
        downloaded = _download_pyproject(repo_slug=repository)
        session.log("\n".join([str(d) for d in downloaded]))

    _clean_pyproject_files()
    _copy_pyproject_files()


pyprojects_dir = Path.cwd() / "example_pyprojects"

if pyprojects_dir.is_dir():
    projects = [
        nox.param(path, id=path.name)
        for path in pyprojects_dir.iterdir()
        if path.is_dir()
    ]
else:
    projects = []


@nox.session()
@nox.parametrize("package", projects)
def bump_pyproject(session: nox.Session, package: str) -> None:
    session.install(".")

    path = pyprojects_dir / package
    session.chdir(path)
    session.log(f"Project: {path.name}")
    shutil.copy2("pyproject.original.toml", "pyproject.toml")

    session.run(
        "bump-minimum-dependencies",
        "--all-groups",
        "--all-extras",
        *session.posargs,
    )

    session.run(
        "diff",
        "--context=0",
        "pyproject.original.toml",
        "pyproject.toml",
        external=True,
        success_codes=[1],
    )


if __name__ == "__main__":
    nox.main()
