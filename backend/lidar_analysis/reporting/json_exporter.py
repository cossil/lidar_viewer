"""JSON export helpers (PRD sec 60; SCHEMAS sec 33-34).

Operates on the canonical serialized objects (dicts( — sensor/scenario/simulation/result —
so the boundary is model-shape-stable and testable without the full engine.
"""

from __future__ import annotations

import json
import os
from typing import Any


def export_json(obj: dict[str, Any], path: str) -> str:
    """Pretty-print + utf8 serialize to path; returns the path. Atomic write (tmp+os.replace.."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False)
    os.replace(tmp, path)
    return path


def dumps_json(obj: dict[str, Any]) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True)