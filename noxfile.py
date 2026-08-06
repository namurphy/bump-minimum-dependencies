# /// script
# python_version = "==3.14"
# dependencies = ["nox[uv]"]
# ///

import nox
import nox_uv
import pathlib

nox.options.default_venv_backend = "uv"

_HERE = pathlib.Path(__file__).parent

MAXPYTHON = "3.14"


@nox_uv.session(python=MAXPYTHON, uv_groups=["lint"])
def lint(session: nox.Session) -> None:
    session.run("prek", "run", "--all-files", "--quiet")


@nox_uv.session(python=MAXPYTHON, uv_groups=["test"])
def test(session: nox.Session) -> None:
    session.run("pytest", "tests", "--tb=short")


@nox_uv.session(python=MAXPYTHON, uv_groups="[ty]")
def ty(session: nox.Session) -> None:
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
