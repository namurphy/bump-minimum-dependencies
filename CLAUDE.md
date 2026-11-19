# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A CLI (`bump-minimum-dependencies`, entry point `bump_minimum_dependencies.main:main`) that raises the lower bounds of requirements in a `pyproject.toml` based on how long ago each minor release first appeared on PyPI, in the spirit of SPEC 0. It changes `pyproject.toml` only by shelling out to `uv add --frozen`; it never writes the TOML itself.

## Commands

The checks are nox sessions (the CI matrix in `.github/workflows/ci.yml` runs the same ones). `noxfile.py` carries inline script metadata, so it can run without nox installed:

```shell
uv run noxfile.py -s test-3.14          # or: nox -s test
nox -s test-3.14 -- tests/test_bump.py::test_bumping_single_package   # single test
nox -s lint                              # prek (pre-commit) on all files
nox -s ty                                # type checking (applies --fix by default)
nox -s test_cli                          # end-to-end CLI test; needs `faketime` installed
nox -s build
```

To skip nox for quick iteration: `uv run pytest tests/test_bump.py -k plasmapy`.

`nox -s download_pyprojects`, followed by `nox -s bump_pyproject`, downloads `pyproject.toml` files from large public projects into `example_pyprojects/` and runs the tool on each, printing a diff. Use it for manual smoke testing, not as a pass/fail check.

## Architecture

- `main.py` defines the click command. It turns CLI options into an `Inputs` object and calls `BumpMinimumDependencies(inputs).run()`. The README's Usage section is a copy of `--help` output, so update it when options change.
- `inputs.py` (`Inputs`) holds the normalized options and computes `today`, `drop_date`, and `cooldown_date` (in UTC) from `--drop-months` and `--cooldown-months`. The `--only-*` options imply skipping the other categories, and that logic lives here.
- `pyproject.py` (`PyProject`) is a read-only view of the TOML file that parses `project.dependencies`, `optional-dependencies`, and `dependency-groups` into `packaging` `Requirement` sets.
- `bump.py` has the core logic, in two layers:
  - `BumpSinglePackage` fetches release metadata from the PyPI Simple JSON API (`https://pypi.org/simple/<name>`, with yanked releases and prereleases excluded) and uses `oldest_supported_release()` to pick the new minimum. That is the oldest minor release between the drop date and the cooldown date, or else the newest one before the drop date. `adjust_micro` then bumps the micro version for pre-1.0 packages or for minors with many micro releases.
  - `combine_requirements` uses `dep_logic` to intersect the original specifier with `>=<new_min>`. When the intersection is empty, it keeps the original. When the result contains `||` (multiple `!=`), it raises `BrokenSpecifierError`.
  - `BumpMinimumDependencies` decides which requirements and categories to update. It skips the project itself, requirements with markers, and URL requirements. It catches per-package failures and logs them as warnings, so one bad package never aborts the run. It then runs a separate `uv add --frozen [--group=X | --optional=X] <req>` for each requirement, or prints the commands with `--dry-run`.
- `logging.py` provides a shared rich-based `logger` and the `package_prefix()` helper used in messages. `utils.py` handles version and requirement normalization and parses PyPI filenames into versions.

## Testing notes

- Tests make live requests to PyPI, so they need network access. Time is pinned with `pytest-freezer` (`freezer.move_to(...)`), and the expected results depend on that date.
- `test_bumping_minimum_requirements` in `tests/test_bump.py` is parametrized over subdirectories of `tests/data/`. Each subdirectory has a `pyproject.toml` and a `pyproject.expected.toml` that must match exactly after the run, including any normalization by uv. By convention, the directory suffix is `<drop>_<cooldown>` months. The steps for adding a case are in `tests/data/README.md`.
- pytest also runs with `--doctest-modules`, so docstring examples in `src/` are executed.

## Conventions

- `requires-python >= 3.13`. Ruff enables a large rule set with numpy-style docstrings (see `pyproject.toml`). Inline suppressions use the `# ruff:ignore[CODE]` form rather than `# noqa`.
- Pre-commit hooks (run by prek) include `pyproject-fmt`, `uv-lock`, `mdformat`, `codespell`, and `typos`, so edits to `pyproject.toml` or Markdown may be reformatted automatically.
