# bump-minimum-dependencies

Automatically bump the minimum allowed versions of dependencies in `pyproject.toml` based on the time since first release, with a cooldown period. ⬆️

Inspired by [SPEC 0]. 🧪

## Motivation

Determining the minimum requirements of a Python package requires balancing competing tradeoffs.
Lengthly support windows increase maintenance burden, prevent developers from using new features and assuming bugfixes, and lead to more complicated code.
Short support windows increase the risk of dependency conflicts.
Automatically bumping minimum requirements in a predictable way saves time and balances these tradeoffs.

## Usage

```groff
Usage: bump-minimum-dependencies [OPTIONS]

  Bump minimum allowed versions of package dependencies in pyproject.toml.

  This tool updates pyproject.toml via `uv add --frozen` to drop support for
  minor versions of package dependencies based on the time since the minor
  version was first released, where package versions may be given by
  `<MAJOR>.<MINOR>` or `<MAJOR>.<MINOR>.<MICRO>`.

  When a `<MAJOR>.<MINOR>` release has numerous micro releases or for pre-1.0
  releases, `<MICRO>` might also be bumped to the last release prior to the
  drop date. Additional constraints such as upper limits are preserved.

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

  - Use uv's `lowest-direct` [resolution strategy] to run tests in an environment containing the minimum versions of direct dependencies.

- This tool invokes `uv add --frozen` to update dependencies in `pyproject.toml` without updating lock files or syncing virtual environments. Requirements may be normalized upon updates.

- Using [dep-logic] allows bump-minimum-dependencies to handle a wide variety of requirements specifiers and perform logical operations to combine multiple requirements specifiers. For example, `>=4.1,<5` and `>=4.2` will be combined into `>=4.2,<5`.

  - If the time-based requirement is mutually exclusive with the original requirement, the original requirement will be preserved.

- Requirements that cannot be updated will be skipped.

## Limitations and caveats

- This tool does not guarantee that an environment can be created that includes the minimum allowed versions of all direct dependencies, but this can be tested with `uv lock --resolution=lowest-direct --dry-run`.

- Requirements that use `==`, `~=`, or multiple `!=` comparisons or non-standard [version specifiers] might not be updated.

- This tool does not update `build-system.requires` or requirements with markers (such as `'setuptools; python_version > "3.11"'`).

## Feature requests and bug reports

To make a feature request, please [raise an issue].

If you discover a bug, please [raise an issue] with a minimal reproducible example (i.e., the `pyproject.toml` file and the `bump-minimum-dependencies` command that was used).

## Related projects

- [scientific-python/spec0-action](https://github.com/scientific-python/spec0-action) — a GitHub action to create quarterly pull requests to perform SPEC 0 updates using a published drop schedule. Unlike `bump-minimum-dependencies`, this tool distinguishes between SPEC 0 core packages and other packages.

- [cgordberg/bump-dependencies](https://github.com/cgoldberg/bump-dependencies) — updates dependency specifiers in `pyproject.toml` to latest compatible versions.

- [hmaarrfk/nep29](https://github.com/hmaarrfk/nep29) — calculator tools for [NEP 29], a precursor to SPEC 0. `nep29` can be used to check the results of `bump-minimum-dependencies`, as in the following example (if uv is installed):

  ```shell
  uvx --python=3.14 --with=setuptools nep29 --n_minor=1 --n_months=12 scipy
  ```

[dep-logic]: https://github.com/pdm-project/dep-logic
[nep 29]: https://github.com/hmaarrfk/nep29
[raise an issue]: https://github.com/namurphy/bump-minimum-dependencies/issues/new
[resolution strategy]: https://docs.astral.sh/uv/concepts/resolution/#resolution-strategy
[spec 0]: https://scientific-python.org/specs/spec-0000
[version specifiers]: https://packaging.python.org/en/latest/specifications/version-specifiers/#version-specifiers
