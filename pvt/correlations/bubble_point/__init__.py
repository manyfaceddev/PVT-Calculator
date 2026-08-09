"""pvt/correlations/bubble_point — Bubble-point pressure correlations.

Four independent correlations live here (almarhoun, glaso, standing,
vasquez_beggs) -- there is deliberately no package-level bare `bubble_point`
name, since that would be ambiguous among the four. Call
`<module>.bubble_point(...)` explicitly, e.g. `standing.bubble_point(...)`.

The sole exception is `standing_bubble_point`, a deprecated
argument-reordering alias for `standing.bubble_point` kept for existing
callers (ui/recombination.py, cli.py) -- see standing.py for details.
"""

from . import almarhoun, glaso, standing, vasquez_beggs
from .standing import standing_bubble_point

__all__ = [
    "almarhoun",
    "glaso",
    "standing",
    "vasquez_beggs",
    "standing_bubble_point",
]
