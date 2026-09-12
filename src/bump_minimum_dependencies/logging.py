"""Define logger tools."""

__all__ = ["logger", "package_prefix"]

import logging
import os
import sys

from rich.logging import RichHandler
from rich.markup import escape

during_testing = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ

keywords: list[str] = [
    "Skipping.",
    "Continuing.",
    "Requirements to update:",
    "frozen",
    "quiet",
    "Combined requirement:",
]

if during_testing:
    handler: logging.Handler = logging.NullHandler()
else:
    handler = RichHandler(
        rich_tracebacks=False,
        show_time=False,
        markup=True,
        keywords=keywords,
        show_path=during_testing,
    )

logging.basicConfig(
    format="%(message)s",
    datefmt="[%X]",
    handlers=[handler],
)

logger: logging.Logger = logging.getLogger("bump-minimum-dependencies")


def package_prefix(package: str) -> str:
    """Create a formatted prefix logger messages for a package."""
    raw_prefix = f"[{package}]"
    if during_testing:
        return raw_prefix
    return f"[magenta]{escape(raw_prefix)}[/magenta]"


def log_uv_command(command: list[str]) -> None:
    command_string = " ".join(command)
    if during_testing:
        msg = f"Running: {command_string}"
    else:
        msg = f"Running: [bold]{command_string}[/bold]"
    logger.info(msg)
