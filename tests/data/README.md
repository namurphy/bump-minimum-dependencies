## Adding test cases

To add a test `pyproject.toml` called `test_case_name`, start from the top-level directory of the git repository and run:

```shell
mkdir test_case_name
cd test_case_name
```

Create an isolated `pyproject.toml`:

```shell
uv init --bare --no-workspace
```

Add the dependencies to test:

```shell
uv add --frozen "matplotlib>=0.81"
```

Create a file for what `pyproject.toml` should change into. It must be exact.

```shell
cp pyproject.toml pyproject.expected.toml
```

Add the test case to the parametrization for `test_pyproject` in `tests/test_bump.py`, including the options to pass to it.
