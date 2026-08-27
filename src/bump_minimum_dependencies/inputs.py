import datetime

__all__ = ["Inputs", "DEFAULT_DROP_MONTHS", "DEFAULT_COOLDOWN_MONTHS", "DAYS_PER_MONTH"]

import math
import functools
from typing import Literal
from pathlib import Path


DEFAULT_DROP_MONTHS = 24
DEFAULT_COOLDOWN_MONTHS = 18

DAYS_PER_MONTH = 30.44


def _make_lower_case_set(iterable: tuple[str, ...] | list[str]) -> set[str]:
    return {s.lower() for s in iterable}


_VerbosityLiteral = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "NOTSET"]


class Inputs:
    """Inputs provided to bump-minimum-dependencies (see main.py for meanings)."""

    def __init__(
        self,
        *,
        pyproject_file: str | Path = Path("pyproject.toml"),
        drop_months: float = 24,
        cooldown_months: float = 18,
        all_extras: bool = False,
        all_groups: bool = False,
        skip_core: bool = False,
        extra: tuple[str, ...] | list[str] = (),
        group: tuple[str, ...] | list[str] = (),
        skip_package: tuple[str, ...] | list[str] = (),
        only_package: tuple[str, ...] | list[str] = (),
        skip_group: tuple[str, ...] | list[str] = (),
        skip_extra: tuple[str, ...] | list[str] = (),
        verbosity: _VerbosityLiteral = "WARNING",
    ):
        """Put the inputs in a more usable form."""
        self.pyproject_file: Path = Path(pyproject_file)
        self.drop_months: float = drop_months
        self.cooldown_months: float = cooldown_months
        self.update_all_groups: bool = all_groups
        self.update_all_extras: bool = all_extras
        self.skip_core_requirements: bool = skip_core
        self.verbosity: _VerbosityLiteral = verbosity
        self.packages_to_skip: set[str] = _make_lower_case_set(skip_package)
        self.packages_to_update: set[str] = _make_lower_case_set(only_package)
        self.extras_to_update: set[str] = _make_lower_case_set(extra)
        self.extras_to_skip: set[str] = _make_lower_case_set(skip_extra)
        self.groups_to_update: set[str] = _make_lower_case_set(group)
        self.groups_to_skip: set[str] = _make_lower_case_set(skip_group)

    @functools.cached_property
    def today(self) -> datetime.date:
        """The date for today in the UTC time zone."""
        return datetime.datetime.now(tz=datetime.timezone.utc).date()

    @functools.cached_property
    def drop_date(self) -> datetime.date:
        """The date drop_months before today."""
        support_window = datetime.timedelta(
            days=math.ceil(self.drop_months * DAYS_PER_MONTH)
        )
        return self.today - support_window

    @functools.cached_property
    def cooldown_date(self) -> datetime.date:
        """The date cooldown_months before today."""
        cooldown_period = datetime.timedelta(
            days=math.ceil(self.cooldown_months * DAYS_PER_MONTH)
        )
        return self.today - cooldown_period
