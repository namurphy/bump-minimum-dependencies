# /// script
# python_version = "==3.14"
# dependencies = ["nox[uv]"]
# ///

import nox
import pathlib

nox.options.default_venv_backend = "uv"

_HERE = pathlib.Path(__file__).parent

MAXPYTHON = "3.14"


@nox.session(python=MAXPYTHON)
def lint(session: nox.Session) -> None:
    session.install(".[test]")
    session.run("prek", "run", "--all-files", "--quiet")


@nox.session(python=MAXPYTHON)
def test(session: nox.Session) -> None:
    session.install(".", ".[test]")
    session.run("pytest", "tests", "--tb=short")


@nox.session(python=MAXPYTHON)
def mypy(session: nox.Session) -> None:
    session.install(".[test]")
    session.run("mypy", ".", "--strict")


@nox.session(python=MAXPYTHON)
def ty(session: nox.Session) -> None:
    session.install(".[test]", "nox")
    session.run("ty", "check", ".")


@nox.session(python=MAXPYTHON)
def build(session: nox.Session) -> None:
    session.run("uv", "build")


@nox.session(python=MAXPYTHON)
def run(session: nox.Session) -> None:
    session.install(".")
    session.run("bump-minimum-dependencies")


if __name__ == "__main__":
    nox.main()
