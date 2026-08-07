# bump-minimum-dependencies

Automagically updates the minimum supported dependencies of a Python package, including dependency groups and optional dependencies.

> [!NOTE]
> This tool is in the early stages of procrastination-driven development (PDD). If you find bugs, please raise an issue!

## Background

This tool was inspired by [SPEC 0 — Minimum Supported Dependencies](https://scientific-python.org/specs/spec-0000), which recommends that projects across the scientific pythoniverse adopt a common time-based policy for dropping dependencies.
SPEC 0 recommends that support for core package dependencies be dropped 2 years after their initial release.

## Limitations

 - By making use of [`dep-logic`](https://github.com/pdm-project/dep-logic), `bump-minimum-dependencies` is able to handle a wide variety of requirements. When a requirement is unable to be updated, `bump-minimum-dependencies` issues a warning and skips making changes to that requirement.
 - Lockfiles are not updated by `bump-minimum-dependencies`, so files like `uv.lock` will need to be updated manually.
 - This tool does not upgrade the minimum required version of Python.

## Related projects

 - [scientific-python/spec0-action](https://github.com/scientific-python/spec0-action) — a GitHub action to create quarterly pull requests to perform SPEC 0 updates using a published drop schedule. Unlike `bump-minimum-dependencies`, this tool distinguishes between SPEC 0 core packages and other packages.
 - [cgordberg/bump-dependencies](https://github.com/cgoldberg/bump-dependencies) — updates dependency specifiers in `pyproject.toml` to latest compatible versions.
