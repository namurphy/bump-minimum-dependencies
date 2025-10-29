# /// script
# python_version = "==3.14"
# dependencies = ["nox[uv]"]
# ///

import nox
import pathlib

nox.options.default_venv_backend = "uv"

_HERE = pathlib.Path(__file__).parent


@nox.session
def lint(session: nox.Session) -> None:
    session.run("uvx", "prek", "run", "--all-files", "--quiet")


@nox.session
def test(session):
    session.install(".")
    session.run("uvx", "pytest", "tests")


@nox.session
def ty(session):
    session.install(".[dev]")
    session.run("uvx", "ty", "check")


if __name__ == "__main__":
    nox.main()
