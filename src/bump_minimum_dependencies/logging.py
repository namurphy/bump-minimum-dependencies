__all__ = ["logger", "package_prefix"]

import logging
from rich.logging import RichHandler


rich_handler = RichHandler(rich_tracebacks=False, show_time=False)


logging.basicConfig(
    format="%(message)s",
    datefmt="[%X]",
    handlers=[rich_handler],
)

logger = logging.getLogger("bump-minimum-dependencies")


def package_prefix(package: str) -> str:
    return f"[{package}] ****"   # add formatting
