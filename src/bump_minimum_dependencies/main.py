__all__ = ["main"]

import pathlib

import click

from . import bump

from typing import Literal

DEFAULT_DROP_MONTHS = 24
DEFAULT_COOLDOWN_MONTHS = 18
DEFAULT_ALL_EXTRAS = False
DEFAULT_ALL_GROUPS = False
DEFAULT_SKIP_CORE = False


@click.command(
    "bump-minimum-dependencies",
    context_settings={"show_default": True},
)
@click.option(
    "--pyproject-file",
    default="pyproject.toml",
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        writable=True,
        readable=True,
    ),
    help="Path to pyproject.toml.",
)
@click.option(
    "--drop-months",
    default=DEFAULT_DROP_MONTHS,
    type=click.FloatRange(min=0, max_open=True),
    help=("Drop minor releases older than this many months ago."),
)
@click.option(
    "--cooldown-months",
    default=DEFAULT_COOLDOWN_MONTHS,
    type=click.FloatRange(min=0, max_open=True),
    help=(
        "Keep at least one release this old, not to exceed drop-months, if possible."
    ),
)
@click.option(
    "--only-package",
    default=[],
    type=click.STRING,
    help=(
        "Name of a package to update. May be provided multiple times. "
        "When this option is used, all other packages will be skipped."
    ),
    multiple=True,
)
@click.option(
    "--skip-package",
    default=[],
    type=click.STRING,
    help="Name of a package to skip when performing updates. Can be used multiple times.",
    multiple=True,
)
@click.option(
    "--extra",
    default=[],
    type=click.STRING,
    help="An optional dependencies category (extra) to update. Can be used multiple times.",
    multiple=True,
)
@click.option(
    "--all-extras",
    default=False,
    is_flag=True,
    help="Update all optional dependencies categories.",
)
@click.option(
    "--skip-extra",
    default=[],
    type=click.STRING,
    help="An optional dependencies category to skip. Can be used multiple times.",
    multiple=True,
)
@click.option(
    "--group",
    default=[],
    type=click.STRING,
    help="A dependency group to update. Can be used multiple times.",
    multiple=True,
)
@click.option(
    "--all-groups",
    default=False,
    is_flag=True,
    help="Update all dependency groups.",
)
@click.option(
    "--skip-group",
    default=[],
    type=click.STRING,
    help="A dependency group to skip. Can be used multiple times.",
    multiple=True,
)
@click.option(
    "--skip-core",
    default=False,
    is_flag=True,
    help="Do not update core project dependencies.",
)
@click.option(
    "--bump-micro",
    default=False,
    is_flag=True,
    help="Drop support for all but the highest micro release before "
    "the drop date. Useful for packages that perform "
    "micro releases in place of minor releases.",
)
@click.option(
    "--verbosity",
    default="WARNING",
    type=click.Choice(
        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"],
    ),
    help="Logging verbosity level.",
)
@click.version_option(package_name="bump_minimum_dependencies")
def main(
    pyproject_file: str | pathlib.Path,
    drop_months: float,
    cooldown_months: float,
    all_extras: bool,
    all_groups: bool,
    skip_core: bool,
    extra: tuple[str, ...] | list[str],
    group: tuple[str, ...] | list[str],
    skip_package: tuple[str, ...] | list[str],
    only_package: tuple[str, ...] | list[str],
    skip_group: tuple[str, ...] | list[str],
    skip_extra: tuple[str, ...] | list[str],
    bump_micro: bool,
    verbosity: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"],
) -> None:
    """
    Bump the minimum allowed minor versions of package dependencies.

    This tool updates pyproject.toml via `uv add --frozen` to drop
    support for minor versions of package dependencies based on the time
    since the minor version was first released, where package versions
    may be given by `<MAJOR>.<MINOR>` or `<MAJOR>.<MINOR>.<PATCH>`.
    Additional constraints such as upper limits are preserved.

    For example, if version `3.4.0` of a package dependency was released
    25 months ago and version `3.5.0` was released 23 months ago,
    running `bump-minimum-dependencies` will update the requirement from
    `>=3.4.0` to `>=3.5.0`.

    Requirements with markers or that cannot be updated will be skipped
    with a warning.
    """

    bump_minimum_dependencies = bump.BumpMinimumDependencies(
        pyproject_file=pyproject_file,
        drop_months=drop_months,
        cooldown_months=cooldown_months,
        all_extras=all_extras,
        all_groups=all_groups,
        extra=extra,
        group=group,
        skip_package=skip_package,
        skip_core=skip_core,
        only_package=only_package,
        verbosity=verbosity,
        skip_group=skip_group,
        skip_extra=skip_extra,
        bump_micro=bump_micro,
    )

    bump_minimum_dependencies.run()
