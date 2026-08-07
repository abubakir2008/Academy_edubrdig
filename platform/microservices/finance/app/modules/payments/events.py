"""Event bus handle for the payments module (publishes only)."""

from __future__ import annotations

from ...events import bus

__all__ = ["bus"]
