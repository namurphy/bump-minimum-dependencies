# bump-minimum-dependencies

Automatically bump the minimum allowed minor versions of Python package dependencies based on the time since first release, with a cooldown period. ⬆️

Inspired by [SPEC 0]. 🧪

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
  minimum-dependencies` will update the requirement from `>=3.4.0` to
  `>=3.5.0`.

  Requirements with markers or that cannot be updated will be skipped with a
  warning.

Options:
  --pyproject-file FILE           Path to pyproject.toml.  [default:
                                  pyproject.toml]
  --drop-months FLOAT RANGE       Drop minor releases older than this many
                                  months ago.  [default: 24; x>=0]
  --cooldown-months FLOAT RANGE   Keep at least one release this old, not to
                                  exceed drop-months, if possible.  [default:
                                  18; x>=0]
  --only-package TEXT             Name of a package to update. May be provided
                                  multiple times. When this option is used,
                                  all other packages will be skipped.
  --skip-package TEXT             Name of a package to skip when performing
                                  updates. Can be used multiple times.
  --extra TEXT                    An optional dependencies category (extra) to
                                  update. Can be used multiple times.
  --all-extras                    Update all optional dependencies categories.
  --skip-extra TEXT               An optional dependencies category to skip.
                                  Can be used multiple times.
  --group TEXT                    A dependency group to update. Can be used
                                  multiple times.
  --all-groups                    Update all dependency groups.
  --skip-group TEXT               A dependency group to skip. Can be used
                                  multiple times.
  --skip-core                     Do not update core project dependencies.
  --verbosity [DEBUG|INFO|WARNING|ERROR|CRITICAL|NOTSET]
                                  Logging verbosity level.  [default: WARNING]
  --version                       Show the version and exit.
  --help                          Show this message and exit.
```

## Examples

To bump core package dependencies using default settings, run:

```shell
bump-minimum-dependencies
```

To bump only plasmapy, run:

```shell
bump-minimum-dependencies --only-package plasmapy
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

To bump all dependency groups but skip the `doc` group, run:

```shell
bump-minimum-dependencies --all-groups --skip-group doc
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

## Usage notes

- Please review and test all updates to `pyproject.toml` before accepting them.

- This tool invokes `uv add --frozen` to update dependencies in `pyproject.toml` without updating lock files or syncing virtual environments.

- Using [`dep-logic`](https://github.com/pdm-project/dep-logic) allows bump-minimum-dependencies to handle a wide variety of requirements specifiers and perform logical operations to combine multiple requirements specifiers. For example, `>=4.1,<5` and `>=4.2` will be combined into `>=4.2,<5`. Some requirements might not be updated, such as those using `==` or `~=`.

- If the time-based requirement is mutually exclusive with the original requirement, the original requirement will be preserved.

- If a particular requirement cannot be updated, it will be skipped.

- Within a given category, dependencies with markers (such as `'setuptools; python_version > "3.11"'`) will not be updated.

- Requirements may be normalized upon updates by `uv add` (e.g., removal of `.0` suffixes and making package names lower case).

## Limitations and caveats

- This tool may be unable to update certain dependencies that use non-standard [version specifiers](https://packaging.python.org/en/latest/specifications/version-specifiers/#version-specifiers) or use `!=` multiple times.

- This tool does not guarantee that an environment can be created that includes the minimum allowed versions of all direct dependencies, but this can be tested with `uv lock --resolution=lowest-direct --dry-run` and then manually fixed.

- This tool does not update `build-system.requires`.

## Motivation

Determining the minimum allowed version of a dependency requires balancing competing tradeoffs. ⚖️
Supporting older versions increases maintenance burden because of the need to support and test a wide range of versions, while also limiting developers from using newer features and assuming bugfixes.
When the range of allowed versions is too large, code can become more complicated to account for various contingencies.
Support windows that are too brief increase the risk of dependency conflicts and may cause problems for end users.
The developer maintenance burden is further increased when developers repeatedly discuss when to drop older versions of dependencies.

[SPEC 0] recommends that projects across the scientific pythoniverse adopt a common time-based policy for dropping support for older versions of dependencies.
SPEC 0 recommends core package dependencies be dropped 24 months after their initial minor release.
NumPy `v2.1.0` was released on 2024-08-18, so SPEC 0 recommends that packages drop support for `v2.1.*` of NumPy after 2026-08-18.

A limitation of SPEC 0 is that when a dependency goes more than 24 months between releases, a new release can immediately become the minimum supported version.
This limitation can be mitigated by providing a cooldown period so that new releases do not become the minimum supported version until a certain time period has passed (such as 12 months).

Because dependency updates have often needed to be performed manually (such as by looking up release times on the Python Package Index and editing `pyproject.toml` accordingly), a tool that automates these updates will save developer time, especially when accounting for edge cases.

## Feature requests and bug reports

To make a feature request, please [raise an issue].

If you discover a bug, please [raise an issue] with a minimal reproducible example (i.e., the `pyproject.toml` file and the `bump-minimum-dependencies` command that was used).

## Related projects

- [scientific-python/spec0-action](https://github.com/scientific-python/spec0-action) — a GitHub action to create quarterly pull requests to perform SPEC 0 updates using a published drop schedule. Unlike `bump-minimum-dependencies`, this tool distinguishes between SPEC 0 core packages and other packages.

- [cgordberg/bump-dependencies](https://github.com/cgoldberg/bump-dependencies) — updates dependency specifiers in `pyproject.toml` to latest compatible versions.

- [hmaarrfk/nep29](https://github.com/hmaarrfk/nep29) — calculator tools for [NEP 29](https://github.com/hmaarrfk/nep29), a precursor to SPEC 0. `nep29` can be used to check the results of `bump-minimum-dependencies`, as in the following example (if uv is installed):

  ```shell
  uvx --python=3.14 --with=setuptools nep29 --n_minor=1 --n_months=12 scipy
  ```

[raise an issue]: https://github.com/namurphy/bump-minimum-dependencies/issues/new
[spec 0]: https://scientific-python.org/specs/spec-0000
