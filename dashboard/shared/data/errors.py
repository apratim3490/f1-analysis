"""Source-agnostic data fetch error."""

from __future__ import annotations


class F1DataError(Exception):
    """Source-agnostic data fetch error. UI catches only this."""
