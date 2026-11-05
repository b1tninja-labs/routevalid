"""role and relationship checks on AS paths (RFC 9234).

Every object in this module is a placeholder until the milestone named in ROADMAP.md lands. A
stub raises instead of returning a plausible empty value: a protocol library that silently
answers nothing is worse than one that refuses to answer.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    LeakVerdict = Any  # placeholder: give it a real type in the milestone that needs it
    Relationships = Any  # placeholder: give it a real type in the milestone that needs it

__all__ = [
    "check_path",
]


def check_path(asn_path: list, relationships: Relationships) -> LeakVerdict:
    """Pending behaviour defined by RFC 9234.

    Not implemented yet. See the ``leak.check_path()`` row in ROADMAP.md; this stub
    raises on purpose so nothing downstream mistakes it for working code.
    """
    raise NotImplementedError("check_path() is not implemented: RFC 9234")
