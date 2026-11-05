"""routevalid -- hijack and leak detection with evidence attached.

Detection tools either are research prototypes or are hosted dashboards you cannot self host.
"""

from __future__ import annotations

from . import apps, cli, event, leak, observe, origin, replay, rules, score, visibility
from .event import emit
from .leak import check_path
from .observe import record
from .origin import check_origin
from .replay import reevaluate
from .score import confidence
from .visibility import announcers

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "announcers",
    "apps",
    "check_origin",
    "check_path",
    "cli",
    "confidence",
    "emit",
    "event",
    "leak",
    "observe",
    "origin",
    "record",
    "reevaluate",
    "replay",
    "rules",
    "score",
    "visibility",
]
