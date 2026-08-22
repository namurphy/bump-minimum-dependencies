# /// script
# python_version = ">=3.13"
# dependencies = ["nox", "nox-uv"]
# ///

import difflib
import filecmp
import shutil
import nox
import nox_uv
from pathlib import Path

nox.options.default_venv_backend = "uv"

_HERE = Path(__file__).parent

supported_python_versions: tuple[str, ...] = ("3.13", "3.14")
maxpython: str = sorted(supported_python_versions)[-1]


@nox_uv.session(python=maxpython, uv_groups=["dev"])
def lint(session: nox.Session) -> None:
    """Run prek on all files."""
    session.run("prek", "run", "--all-files", "--quiet")


@nox_uv.session(python=supported_python_versions, uv_groups=["dev"])
def test(session: nox.Session) -> None:
    """Run tests."""
    session.run(
        "pytest",
        ".",
        "--tb=short",
        "--doctest-modules",
        "--doctest-continue-on-failure",
    )


@nox_uv.session(python=maxpython, uv_groups=["dev"])
def ty(session: nox.Session) -> None:
    """Perform static type checking with ty."""
    args = session.posargs or ["--fix"]
    session.run("ty", "check", ".", *args)


@nox.session(python=supported_python_versions)
def build(session: nox.Session) -> None:
    """Build the package."""
    session.run("uv", "build")


@nox.session(python=supported_python_versions)
def run(session: nox.Session) -> None:
    """Run the package."""
    session.install(".")
    session.run("bump-minimum-dependencies")


@nox.session(python=supported_python_versions)
def test_cli(session: nox.Session):
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

    # Prepend faketime CLI wrapper to intercept child process OS calls
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


if __name__ == "__main__":
    nox.main()
