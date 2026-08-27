__all__ = ["main"]

import pathlib

import click

from click.core import ParameterSource

from . import bump
from bump_minimum_dependencies.inputs import (
    DEFAULT_DROP_MONTHS,
    DEFAULT_COOLDOWN_MONTHS,
    Inputs,
)

from typing import Literal


@click.command(
    name="bump-minimum-dependencies",
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
    help=("Keep at least one minor release this old when possible."),
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
    help="A package to skip when performing updates. Can be used multiple times.",
    multiple=True,
)
@click.option(
    "--no-extras",
    default=False,
    is_flag=True,
    help="Do not update extras, except if specified by --only-extra.",
)
@click.option(
    "--only-extra",
    default=[],
    type=click.STRING,
    help="An extra to update. Can be used multiple times. Implies --no-extras and --no-groups.",
    multiple=True,
)
@click.option(
    "--skip-extra",
    default=[],
    type=click.STRING,
    help="An extra to not be updated. Can use multiple times.",
    multiple=True,
)
@click.option(
    "--only-group",
    default=[],
    type=click.STRING,
    help="A dependency group to update. Can use multiple times. Implies --no-extras and --no-groups.",
    multiple=True,
)
@click.option(
    "--no-groups",
    default=False,
    is_flag=True,
    help="Do not update dependency groups, except if specified by --only-group.",
)
@click.option(
    "--skip-group",
    default=[],
    type=click.STRING,
    help="A dependency group to skip. Can use multiple times.",
    multiple=True,
)
@click.option(
    "--skip-core",
    default=False,
    is_flag=True,
    help="Do not update core project dependencies.",
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
@click.pass_context
def main(
    ctx: click.Context,
    pyproject_file: str | pathlib.Path,
    drop_months: float,
    cooldown_months: float,
    no_extras: bool,
    no_groups: bool,
    skip_core: bool,
    only_extra: tuple[str, ...] | list[str],
    only_group: tuple[str, ...] | list[str],
    skip_package: tuple[str, ...] | list[str],
    only_package: tuple[str, ...] | list[str],
    skip_group: tuple[str, ...] | list[str],
    skip_extra: tuple[str, ...] | list[str],
    verbosity: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"],
) -> None:
    """
    Bump minimum allowed versions of package dependencies in pyproject.toml.

    This tool updates pyproject.toml via `uv add --frozen` to drop
    support for minor versions of package dependencies based on the time
    since the minor version was first released, where package versions
    may be given by `<MAJOR>.<MINOR>` or `<MAJOR>.<MINOR>.<MICRO>`.

    When a `<MAJOR>.<MINOR>` release has numerous micro releases or for
    pre-1.0 releases, `<MICRO>` might also be bumped to the last release
    prior to the drop date. Additional constraints such as upper limits
    are preserved.

    Requirements with markers or that cannot be updated will be skipped
    with a warning.

    "Groups" refers to dependency groups while "extras" refers to
    categories of optional dependencies.
    """

    if only_group or only_extra:
        no_extras = True
        no_groups = True

    if cooldown_months > drop_months:
        cooldown_months_was_provided: bool = (
            ctx.get_parameter_source("cooldown_months") == ParameterSource.COMMANDLINE
        )
        if cooldown_months_was_provided:
            msg = (
                f"--cooldown-months={cooldown_months} cannot "
                f"exceed --drop-months={drop_months}."
            )
            raise click.ClickException(msg)
        cooldown_months = min(cooldown_months, drop_months)

    inputs = Inputs(
        no_extras=no_extras,
        no_groups=no_groups,
        cooldown_months=cooldown_months,
        drop_months=drop_months,
        only_extra=only_extra,
        only_group=only_group,
        only_package=only_package,
        pyproject_file=pyproject_file,
        skip_core=skip_core,
        skip_extra=skip_extra,
        skip_group=skip_group,
        skip_package=skip_package,
        verbosity=verbosity,
    )

    bump_minimum_dependencies = bump.BumpMinimumDependencies(inputs=inputs)
    bump_minimum_dependencies.run()
