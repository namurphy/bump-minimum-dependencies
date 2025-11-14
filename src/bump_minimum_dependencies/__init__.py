__all__ = ["bump", "main"]

import click

from . import bump


@click.command()
@click.option(
    "--pyproject_file", default="pyproject.toml", help="Path to pyproject.toml"
)
@click.option(
    "--drop_months", default=24, help="Drop releases from this many months ago."
)
@click.option(
    "--cooldown_months",
    default=12,
    help="Ensure that there is at least one release this many months old.",
)
def main(
    pyproject_file: str,
    drop_months: int,
    cooldown_months: int,
) -> None:
    bump.bump_minimum_dependencies(
        pyproject_file=pyproject_file,
        drop_months=drop_months,
        cooldown_months=cooldown_months,
    )
