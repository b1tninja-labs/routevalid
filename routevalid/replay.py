"""deterministic re-evaluation of history against a rule set.

Every object in this module is a placeholder until the milestone named in ROADMAP.md lands. A
stub raises instead of returning a plausible empty value: a protocol library that silently
answers nothing is worse than one that refuses to answer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from typing import Any

    Rules = Any  # placeholder: give it a real type in the milestone that needs it
    Store = Any  # placeholder: give it a real type in the milestone that needs it

__all__ = [
    "reevaluate",
]


def reevaluate(store: Store, rules: Rules, since: datetime) -> list:
    """Pending behaviour defined by RFC 9324.

    Not implemented yet. See the ``replay.reevaluate()`` row in ROADMAP.md; this stub
    raises on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("reevaluate() is not implemented: RFC 9324")
