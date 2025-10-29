import click


@click.command()
@click.option("pyproject_file", default="pyproject.toml", help="Path to pyproject.toml")
@click.option("months", default=24, help="Drop releases from this many months ago.")
@click.option(
    "buffer",
    default=6,
    help="Ensure that there is at least one release this many months old.",
)
@click.option(
    "python_months", default=36, help="Drop Python releases from this many months ago."
)
@click.option(
    "date", default="today", help="Date to use instead of today (YYYY-MM-DD)."
)
def main(
    pyproject_file: str, months: str, buffer: str, python_months: str, date: str
) -> None:
    click.echo(pyproject_file)
    click.echo(months)
    click.echo(buffer)
    click.echo(python_months)
    click.echo(date)
