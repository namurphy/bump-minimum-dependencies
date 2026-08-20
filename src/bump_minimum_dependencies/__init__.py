__all__ = ["bump", "main"]

import pathlib

import click

from . import bump


DEFAULT_DROP_MONTHS = 24
DEFAULT_COOLDOWN_MONTHS = 12
DEFAULT_ALL_EXTRAS = False
DEFAULT_ALL_GROUPS = False
DEFAULT_SKIP_CORE = False


@click.command()
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
    help="Path to pyproject.toml. Default is pyproject.toml in current directory.",
)
@click.option(
    "--drop-months",
    default=DEFAULT_DROP_MONTHS,
    type=click.FloatRange(min=0, max_open=True),
    help=(
        f"Drop minor releases older than this many months ago. Defaults "
        f"to {DEFAULT_DROP_MONTHS}."
    ),
)
@click.option(
    "--cooldown-months",
    default=DEFAULT_COOLDOWN_MONTHS,
    type=click.FloatRange(min=0, max_open=True),
    help=(
        f"Ensure that there is at least one release this many months "
        f"old, if possible. Defaults to {DEFAULT_COOLDOWN_MONTHS} or "
        f"the value provided to --drop-months, whichever is smaller."
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
)
@click.option(
    "--skip-package",
    default=[],
    type=click.STRING,
    help="Name of a package to skip when performing updates. May be provided multiple times.",
    multiple=True,
)
@click.option(
    "--extra",
    default=[],
    type=click.STRING,
    help="Name of an optional dependencies category to update. May be provided multiple times.",
    multiple=True,
)
@click.option(
    "--all-extras",
    default=False,
    is_flag=True,
    help="If provided, all optional dependency categories will be updated.",
)
@click.option(
    "--group",
    default=[],
    type=click.STRING,
    help="Name of a dependency group to update. May be provided multiple times.",
    multiple=True,
)
@click.option(
    "--all-groups",
    default=False,
    is_flag=True,
    help="If provided, all dependency groups will be updated.",
)
@click.option(
    "--skip-core",
    default=False,
    is_flag=True,
    help="If provided, core project dependencies will not be updated.",
)
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

    if cooldown_months > drop_months:
        raise click.BadParameter("cooldown_months cannot exceed drop_months.")

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
    )

    bump_minimum_dependencies.run()
