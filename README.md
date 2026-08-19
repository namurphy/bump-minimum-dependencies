# bump-minimum-dependencies

Automatically bump the minimum allowed minor versions of package dependencies based on the time since first release, with a cooldown period.

## Motivation

This tool was inspired by [SPEC 0], which recommends that projects across the scientific pythoniverse adopt a common time-based policy for dropping dependencies.
SPEC 0 recommends that support for core package dependencies be dropped 24 months after their initial minor release.
For example, NumPy `v2.1.0` was released on 2024-08-18, so SPEC 0 recommends that packages drop support for `v2.1.*` of NumPy after 2026-08-18.

SPEC 0 states:

> Limiting the scope of supported dependencies is an effective way for packages to limit maintenance burden. Combinations of packages need to be tested, which impacts also on continuous integration times and infrastructure upkeep. Code itself also becomes more complicated when it has to be aware of various combinations of configurations.
>
> Adoption of this SPEC will ensure a consistent support policy across packages, and reduce the need for individual projects to devise similar policies.
>
> Ultimately, reduced maintenance burden frees up developer time, which translates into more features, bugfixes, and optimizations for users.

A limitation of following the SPEC 0 recommendations is that when a dependency goes more than 24 months between releases, a new release can immediately become the minimum supported version.
This limitation can be mitigated by providing a cooldown period so that new releases do not become the minimum supported version until a certain time period has passed.

## Usage

```groff
Usage: bump-minimum-dependencies [OPTIONS]

  Bump the minimum allowed minor versions of package dependencies.

  This tool updates pyproject.toml via `uv add --frozen` to drop support for
  minor versions of package dependencies based on the time since the minor
  version was first released, where package versions may be given by
  `<MAJOR>.<MINOR>` or `<MAJOR>.<MINOR>.<PATCH>`. Additional constraints such
  as upper limits are preserved.

  For example, if version `3.4.0` of a package dependency was released 25
  months ago and version `3.5.0` was released 23 months ago, running `bump-
  minimum-dependencies` will change a requirement specifier of that package
  from `>=3.4.0` to `>=3.5.0`.

  Requirements with markers or that cannot be updated will be skipped with a
  warning.

Options:
  --pyproject-file FILE          Path to pyproject.toml. Defaults to
                                 pyproject.toml in current directory.
  --skip-package TEXT            Name of a package to skip when performing
                                 updates. May be provided multiple times.
  --drop-months FLOAT RANGE      Drop minor releases from this many months
                                 ago. Defaults to 24.  [x>=0]
  --cooldown-months FLOAT RANGE  Ensure that there is at least one release
                                 this many months old, if possible. Defaults
                                 to 12.  [x>=0]
  --all-extras                   Flag to update all optional dependencies.
                                 Defaults to false.
  --all-groups                   Flag to update all dependency groups.
                                 Defaults to false.
  --skip-core                    Flag to skip updating core project
                                 dependencies. Defaults to false.
  --extra TEXT                   Name of an optional dependencies category.
                                 May be provided multiple times.
  --group TEXT                   Name of a dependency group to update. May be
                                 provided multiple times.
  --help                         Show this message and exit.
```

## Examples

To bump core package dependencies using default settings, run:

```shell
bump-minimum-dependencies
```

To skip updates for numpy and plasmapy, run:

```shell
bump-minimum-dependencies --skip-package numpy --skip-package plasmapy
```

To drop minor versions older than 36 months with a cooldown of 24 months, run:

```shell
bump-minimum-dependencies --drop-months 36 --cooldown-months 24
```

To bump all optional dependencies (extras), run:

```shell
bump-minimum-dependencies --all-extras
```

To bump all dependency groups, run:

```shell
bump-minimum-dependencies --all-groups
```

To bump the optional dependency (extras) category 'optionals' and
skip updates of core dependencies, run:

```shell
bump-minimum-dependencies --skip-core --extra optionals
```

To bump the dependency group named dev and core dependencies, run:

```shell
bump-minimum-dependencies --extra dev
```

## Notes

- Please review all updates to dependencies before accepting them, including to make sure that comments are satisfactorily preserved.

- Requirements may be normalized upon updates.

  - `.0` suffixes may be removed, since `X.Y` and `X.Y.0` "are not considered distinct release numbers" as per [PEP 440](https://peps.python.org/pep-0440).
  - Package names, which are case-insensitive, may be made lower case.

- The tool uses uv to update `pyproject.toml`, but does not automatically update lockfiles or sync virtual environments. Commands like `uv lock` and `uv sync` would need to be run separately afterward.

- Using [`dep-logic`](https://github.com/pdm-project/dep-logic) allows `bump-minimum-dependencies` to handle a wide variety of requirements specifiers and perform logical operations to combine multiple requirements specifiers. For example, `>=4.1,<5` and `>=4.2` will be combined into `>=4.2,<5`.

  - If the time-based requirement is mutually exclusive with the original requirement, the original requirement will be preserved.
  - Because not all cases can be handled cleanly, `bump-minimum-dependencies` skips updates that it cannot perform (such as when there are multiple `!=` operations in the resulting requirement, as of `dep-logic==0.7.1`).

- If a dependency has a marker within a particular category, the dependency will not be updated.

- If a README or license file is declared in `pyproject.toml`, they must be present so that `pyproject.toml` can be loaded by [pyproject-parser.PyProject.load()](https://pyproject-parser.readthedocs.io/en/latest/api/pyproject-parser.html#pyproject_parser.PyProject.load).

- This tool does not upgrade the minimum required version of Python.

## Feature requests and bug reports

Because `bump-minimum-dependencies` is new, there may be some bugs related to edge cases.
We encourage you to report them with a minimum reproducible example (i.e., your `pyproject.toml` with the `bump-minimum-dependencies` command).

Please also submit feature requests that would make `bump-minimum-dependencies` more helpful to your projects.

## Related projects

- [scientific-python/spec0-action](https://github.com/scientific-python/spec0-action) — a GitHub action to create quarterly pull requests to perform SPEC 0 updates using a published drop schedule. Unlike `bump-minimum-dependencies`, this tool distinguishes between SPEC 0 core packages and other packages.

- [cgordberg/bump-dependencies](https://github.com/cgoldberg/bump-dependencies) — updates dependency specifiers in `pyproject.toml` to latest compatible versions.

- [hmaarrfk/nep29](https://github.com/hmaarrfk/nep29) — calculator tools for [NEP 29](https://github.com/hmaarrfk/nep29), a precursor to SPEC 0. `nep29` can be used to check the results of `bump-minimum-dependencies`, as in the following example (if uv is installed):

  ```shell
  uvx --python=3.14 --with=setuptools nep29 --n_minor=1 --n_months=12 scipy
  ```

- [tox-dev/pyproject-fmt](https://pyproject-fmt.readthedocs.io/en/latest/index.html) — an opinionated formatter for `pyproject.toml` files

[spec 0]: https://scientific-python.org/specs/spec-0000
