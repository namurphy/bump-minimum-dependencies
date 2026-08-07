__all__ = ["bump", "main"]

import click

from . import bump


@click.command()
@click.option(
    "--pyproject_file",
    default="pyproject.toml",
    help="Path to pyproject.toml",
)
@click.option(
    "--drop-months",
    default=24,
    help="Drop minor releases from this many months ago.",
)
@click.option(
    "--cooldown-months",
    default=12,
    help="Ensure that there is at least one release this many months old.",
)
@click.option(
    "--all-extras",
    default=False,
    is_flag=True,
    help="Update all optional dependencies.",
)
@click.option(
    "--all-groups", default=False, is_flag=True, help="Update all dependency groups."
)
@click.option(
    "--extra",
    default=[],
    help="Name of an optional dependencies category. May be provided more than once.",
    multiple=True,
)
@click.option(
    "--group",
    default=[],
    help="Name of a dependency group to update. May be provided more than once.",
    multiple=True,
)
@click.option(
    "--skip",
    default=[],
    help="Name of a package to skip when performing updates. May be provided more than once.",
    multiple=True,
)
def main(
    pyproject_file: str,
    drop_months: int,
    cooldown_months: int,
    all_extras: bool,
    all_groups: bool,
    extra: tuple[str, ...] | list[str],
    group: tuple[str, ...] | list[str],
    skip: tuple[str, ...] | list[str],
) -> None:
    """Bump the minimum allowed versions of package dependencies."""
    bump.bump_minimum_dependencies(
        pyproject_file=pyproject_file,
        drop_months=drop_months,
        cooldown_months=cooldown_months,
        all_extras=all_extras,
        all_groups=all_groups,
        extra=extra,
        group=group,
        skip=skip,
    )
