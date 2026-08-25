__all__ = ["main"]

import pathlib

import click

from . import bump

from typing import Literal


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
    default=bump.DEFAULT_DROP_MONTHS,
    type=click.FloatRange(min=0, max_open=True),
    help=("Drop minor releases older than this many months ago."),
)
@click.option(
    "--cooldown-months",
    default=bump.DEFAULT_COOLDOWN_MONTHS,
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
    )

    bump_minimum_dependencies.run()
