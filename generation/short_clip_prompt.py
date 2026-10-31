"""Focus an image-to-video prompt on one observable change in a short clip."""

from __future__ import annotations

import re


_SETUP = re.compile(r"^(show|present|introduce|state|display|draw)\b", re.I)
_HOLD = re.compile(r"^(hold|end with|near completion)\b", re.I)


def select_action(case: dict) -> str:
    beats = [str(beat).strip() for beat in case.get("expected_narrative_order", [])
             if str(beat).strip()]
    actions = [beat for beat in beats if not _SETUP.match(beat) and not _HOLD.match(beat)]
    if actions:
        return actions[-1]
    return beats[-1] if beats else "make one small, meaningful change in the diagram"


def focused_prompt(case: dict, duration_s: float) -> str:
    """Treat the supplied first frame as a fixed visual specification.

    The original task remains in the dataset for evaluation; this prompt only
    narrows what the model is asked to animate within a few seconds.
    """
    if duration_s <= 0:
        raise ValueError("duration_s must be positive")
    action = select_action(case).rstrip(". ")
    return (
        f"Create one {duration_s:.1f}-second continuous educational animation "
        "from the supplied first frame. Preserve the existing composition, "
        "objects, diagrams, equations, numbers, labels, and spelling exactly. "
        f"Show only this visible change: {action}. "
        "Keep the camera fixed. Make the change visible and then hold its final "
        "state briefly. Do not add new text, symbols, hands, people, objects, "
        "decorations, or a scene cut. Do not redraw or alter existing text."
    )
