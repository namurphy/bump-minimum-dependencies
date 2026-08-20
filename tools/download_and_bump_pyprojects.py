# /// script
# requires-python = ">=3.14"
# dependencies = ["requests", "tomli_w"]
# ///


from pathlib import Path
import requests

import subprocess


import shutil

import warnings


import tomllib
import tomli_w


def download_pyproject(
    repo_slug: str,
) -> list[Path]:
    """Download the `pyproject.toml` file from a GitHub repository.

    Parameters
    ----------
    repo_slug : str
        The GitHub repository target formatted as "OWNER/REPO".

    Returns
    -------
    list of Path
        Paths to the downloaded local files, or an empty list if not found.
    """
    file_name = "pyproject.toml"
    api_url = f"https://api.github.com/repos/{repo_slug}/contents/{file_name}"
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Python-GH-File-Fetcher",
    }

    response = requests.get(api_url, headers=headers, timeout=10)

    if response.status_code == 404:
        warnings.warn(
            f"'{file_name}' not found in repository '{repo_slug}'. Skipping download.",
            UserWarning,
            stacklevel=2,
        )
        return []

    response.raise_for_status()
    item = response.json()

    download_url = item.get("download_url")
    if not download_url:
        warnings.warn(
            f"Could not retrieve download URL for '{file_name}' in '{repo_slug}'.",
            UserWarning,
            stacklevel=2,
        )
        return []

    # Create the subdirectory only after confirming the file exists
    output_dir = repo_slug.split("/")[1]
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_resp = requests.get(
        download_url,
        headers={"User-Agent": "Python-GH-File-Fetcher"},
        timeout=10,
    )
    file_resp.raise_for_status()

    dest_file = output_path / file_name
    dest_file.write_bytes(file_resp.content)

    return [dest_file]


def clean_pyproject_files(root_dir: str | Path = ".") -> list[Path]:
    """
    Recursively find pyproject.toml files in subdirectories and remove
    `project.license-files` and `project.readme` fields.

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

    # Search for pyproject.toml files in subdirectories (excluding root itself if desired)
    for file_path in root_path.rglob("pyproject.toml"):
        if file_path.parent == root_path:
            continue

        with file_path.open("rb") as f:
            data = tomllib.load(f)

        project_table = data.get("project")
        if not isinstance(project_table, dict):
            continue

        # Check if target keys exist
        has_license_files = "license-files" in project_table
        has_readme = "readme" in project_table

        if not (has_license_files or has_readme):
            continue

        # Remove keys
        project_table.pop("license-files", None)
        project_table.pop("readme", None)

        # Write modified content back
        with file_path.open("wb") as f:
            tomli_w.dump(data, f)

        modified_files.append(file_path)

    return modified_files


def copy_pyproject_files(
    target_name: str,
    root_dir: str | Path = ".",
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


def bump_all_subdirectories() -> None:
    """Run `uvx bump-minimum-dependencies` in every immediate subdirectory."""
    current_dir = Path.cwd()

    for path in current_dir.iterdir():
        if path.is_dir():
            print(f"Processing: {path.name}")
            try:
                subprocess.run(
                    [
                        # "uvx",
                        "bump-minimum-dependencies",
                        # "--all-groups",
                        # "--all-extras",
                    ],
                    cwd=path,
                    check=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                print(f"Failed in {path.name}: {e}")


def main() -> None:
    repositories = [
        "ansible/ansible",
        "apache/airflow",
        "astropy/astropy",
        "celery/celery",
        "django/django",
        "fastapi/fastapi",
        "home-assistant/core",
        "indygreg/python-build-standalone",
        "jax-ml/jax",
        "matplotlib/matplotlib",
        "numpy/numpy",
        "pallets/flask",
        "pandas-dev/pandas",
        "PlasmaPy/PlasmaPy",
        "pydantic/pydantic",
        "pypa/pip",
        "pytest-dev/pytest",
        "python-poetry/poetry",
        "pytorch/pytorch",
        "pyvista/pyvista",
        "scikit-image/scikit-image",
        "scikit-learn/scikit-learn",
        "scipy/scipy",
        "sqlalchemy/sqlalchemy",
        "sunpy/sunpy",
        "sympy/sympy",
        "yt-project/yt",
        "namurphy/bump-minimum-dependencies",
    ]

    for repository in repositories:
        downloaded = download_pyproject(repository)
        print([str(p) for p in downloaded])

    clean_pyproject_files()

    copy_pyproject_files("pyproject.original.toml")

    bump_all_subdirectories()


if __name__ == "__main__":
    main()
