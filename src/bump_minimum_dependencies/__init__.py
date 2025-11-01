import click

from . import bump


@click.command()
@click.option(
    "--pyproject_file", default="pyproject.toml", help="Path to pyproject.toml"
)
@click.option("--months", default=24, help="Drop releases from this many months ago.")
@click.option(
    "--buffer",
    default=0,
    help="Ensure that there is at least one release this many months old.",
)
def main(
    pyproject_file: str,
    months: int,
    buffer: int,
) -> None:
    bump.bump_minimum_dependencies(
        pyproject_file=pyproject_file,
        months=months,
        buffer=buffer,
    )
