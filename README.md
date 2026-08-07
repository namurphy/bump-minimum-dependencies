# bump-minimum-dependencies

Automatically updates the minimum supported dependencies of a Python package, including dependency groups and optional dependencies.

Updates to `pyproject.toml` are made with [uv](https://docs.astral.sh/uv).

> [!NOTE]
> This tool is in the early stages of procrastination-driven development (PDD). If you find bugs, please raise an issue!

## Usage

```groff
Usage: bump-minimum-dependencies [OPTIONS]

  Bump the minimum allowed versions of package dependencies.

Options:
  --pyproject_file TEXT      Path to pyproject.toml
  --drop-months INTEGER      Drop minor releases from this many months
                             ago.
  --cooldown-months INTEGER  Ensure that there is at least one release
                             this many months old.
  --all-extras               Update all optional dependencies.
  --all-groups               Update all dependency groups.
  --extra TEXT               Name of an optional dependencies category.
                             May be provided more than once.
  --group TEXT               Name of a dependency group to update. May be
                             provided more than once.
  --skip TEXT                Name of a package to skip when performing
                             updates. May be provided more than once.
  --help                     Show this message and exit.
```

## Background

This tool was inspired by [SPEC 0 — Minimum Supported Dependencies](https://scientific-python.org/specs/spec-0000), which recommends that projects across the scientific pythoniverse adopt a common time-based policy for dropping dependencies.
SPEC 0 recommends that support for core package dependencies be dropped 2 years after their initial release.

## Limitations

- This tool does not upgrade the minimum required version of Python.

- By making use of [`dep-logic`](https://github.com/pdm-project/dep-logic), `bump-minimum-dependencies` is able to handle a wide variety of requirements. When a requirement is unable to be updated, `bump-minimum-dependencies` issues a warning and skips making changes to that requirement.

- This tool does not automatically update lockfiles or sync virtual environments. These commands would need to be performed automatically.

- This tool removes `.0` suffixes when updating requirements for consistency with [pyproject-fmt](https://pyproject-fmt.readthedocs.io/en/latest/index.html).

- The locations of comments may be changed when uv updates `pyproject.toml`, so changes should be reviewed before being accepted.

## Related projects

- [scientific-python/spec0-action](https://github.com/scientific-python/spec0-action) — a GitHub action to create quarterly pull requests to perform SPEC 0 updates using a published drop schedule. Unlike `bump-minimum-dependencies`, this tool distinguishes between SPEC 0 core packages and other packages.
- [cgordberg/bump-dependencies](https://github.com/cgoldberg/bump-dependencies) — updates dependency specifiers in `pyproject.toml` to latest compatible versions.
