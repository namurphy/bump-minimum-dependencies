__all__ = ["logger", "package_prefix"]

import logging
from rich.logging import RichHandler
from rich.markup import escape

keywords = [
    "Skipping.",
    "Continuing.",
    "Requirements to update:",
    "frozen",
    "quiet",
    "Combined requirement:",
]

rich_handler = RichHandler(
    rich_tracebacks=False,
    show_time=False,
    markup=True,
    keywords=keywords,
)


logging.basicConfig(
    format="%(message)s",
    datefmt="[%X]",
    handlers=[rich_handler],
)

logger = logging.getLogger("bump-minimum-dependencies")


def package_prefix(package: str) -> str:
    raw_prefix = f"[{package}]"
    return f"[magenta]{escape(raw_prefix)}[/magenta]"


def log_uv_command(command: list[str]):
    command_string = " ".join(command)

    logger.info(
        f"Running: [bold]{command_string}[/bold]",
        extra={"markup": True},
    )
