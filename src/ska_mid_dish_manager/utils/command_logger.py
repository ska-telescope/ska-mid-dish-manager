"""Shared methods in package."""

# pylint: disable=chained-comparison,invalid-name
from typing import Any

from tango import InfoIt


class BaseInfoIt(InfoIt):
    """Update Tango InfoIt to not truncate the result."""

    def _LogIt__compact_elem(self, v: Any, **_: Any) -> str:
        """Just return the item as is."""
        v = repr(v)
        return v
