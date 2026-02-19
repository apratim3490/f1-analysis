"""Query filter builder for OpenF1 API comparison operators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Filter:
    """Represents a comparison filter for API query parameters.

    Usage:
        # Greater than or equal
        Filter(gte=5)  # produces: param>=5

        # Range filter
        Filter(gte=5, lte=10)  # produces: param>=5&param<=10

        # Less than
        Filter(lt=100)  # produces: param<100
    """

    gt: int | float | str | None = None
    gte: int | float | str | None = None
    lt: int | float | str | None = None
    lte: int | float | str | None = None

    def to_params(self, key: str) -> list[tuple[str, str]]:
        """Convert this filter to a list of (key_with_operator, value) pairs."""
        params: list[tuple[str, str]] = []
        if self.gt is not None:
            params.append((f"{key}>", str(self.gt)))
        if self.gte is not None:
            params.append((f"{key}>=", str(self.gte)))
        if self.lt is not None:
            params.append((f"{key}<", str(self.lt)))
        if self.lte is not None:
            params.append((f"{key}<=", str(self.lte)))
        return params


def build_query_params(**kwargs: Any) -> list[tuple[str, str]]:
    """Build a list of query parameter tuples from keyword arguments.

    Plain values become equality filters. Filter instances become comparison operators.

    Args:
        **kwargs: Keyword arguments where keys are parameter names and values are
                  either plain values (for equality) or Filter instances (for comparisons).

    Returns:
        List of (key, value) tuples suitable for httpx params.
    """
    params: list[tuple[str, str]] = []
    for key, value in kwargs.items():
        if value is None:
            continue
        if isinstance(value, Filter):
            params.extend(value.to_params(key))
        else:
            params.append((key, str(value)))
    return params
