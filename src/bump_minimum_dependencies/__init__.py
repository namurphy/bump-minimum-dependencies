import click

from . import bump


@click.command()
@click.option(
    "--pyproject_file", default="pyproject.toml", help="Path to pyproject.toml"
)
@click.option("--months", default=24, help="Drop releases from this many months ago.")
@click.option(
    "--buffer",
    default=6,
    help="Ensure that there is at least one release this many months old.",
)
@click.option(
    "--python_months",
    default=36,
    help="Drop Python releases from this many months ago.",
)
@click.option(
    "--date",
    default="today",
    help="Date to use instead of today (YYYY-MM-DD).",
)
def main(
    pyproject_file: str,
    months: int,
    buffer: int,
    python_months: int,
    date: str,
) -> None:
    bump.bump_minimum_dependencies(
        pyproject_file=pyproject_file,
        months=months,
        buffer=buffer,
        python_months=python_months,
        date=date,
    )
