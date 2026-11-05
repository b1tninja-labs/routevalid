"""prefix and AS visibility tracking over collectors and time.

Every object in this module is a placeholder until the milestone named in ROADMAP.md lands. A
stub raises instead of returning a plausible empty value: a protocol library that silently
answers nothing is worse than one that refuses to answer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import timedelta

__all__ = [
    "announcers",
]


def announcers(prefix: str, window: timedelta) -> list:
    """Pending behaviour defined by design.

    Not implemented yet. See the ``visibility.announcers()`` row in ROADMAP.md; this stub
    raises on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("announcers() is not implemented: design")
