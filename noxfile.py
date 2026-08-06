# /// script
# python_version = ">=3.13"
# dependencies = ["nox", "nox-uv"]
# ///

import nox
import nox_uv
import pathlib

nox.options.default_venv_backend = "uv"

_HERE = pathlib.Path(__file__).parent

supported_python_versions: tuple[str, ...] = ("3.13", "3.14")
maxpython: str = sorted(supported_python_versions)[-1]


@nox_uv.session(python=maxpython, uv_groups=["dev"])
def lint(session: nox.Session) -> None:
    """Run prek on all files."""
    session.run("prek", "run", "--all-files", "--quiet")


@nox_uv.session(python=supported_python_versions, uv_groups=["dev"])
def test(session: nox.Session) -> None:
    """Run tests."""
    session.run("pytest", "tests", "--tb=short")


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


if __name__ == "__main__":
    nox.main()
