"""Compile-time JSON Schema dict documents and a validator helper.

Loads schema JSON files extracted from the formal SCHEMAS spec (sections 3-11).
Provides ``SCHEMAS`` dict and ``validate_json_schema()`` for contract tests.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

_SCHEMA_DIR = Path(__file__).parent / "schemas"

SCHEMAS: Dict[str, dict] = {}
for p in sorted(_SCHEMA_DIR.glob("*.json")):
    SCHEMAS[p.name] = json.loads(p.read_text(encoding="utf-8"))


def _build_registry() -> Registry:
    """Build a referencing Registry so ``$ref`` paths like ``provenance.json`` resolve."""
    from referencing.jsonschema import DRAFT202012

    reg: Registry = Registry()
    for name, schema in SCHEMAS.items():
        if "$schema" not in schema:
            schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        uri = schema.get("$id", f"https://lidar-analysis.local/schema/{name}")
        resource = Resource.from_contents(schema, default_specification=DRAFT202012)
        reg = reg.with_resource(uri, resource)
    return reg


_REGISTRY = _build_registry()


def validate_json_schema(instance: dict, schema_name: str) -> list[str]:
    """Validate *instance* against the named schema.

    Parameters
    ----------
    instance:
        The dict to validate (typically from ``model.model_dump()``).
    schema_name:
        Key into ``SCHEMAS`` (e.g. ``"sensor.json"``).

    Returns
    -------
    list[str]
        Human-readable error messages.  Empty list means valid.
    """
    schema = SCHEMAS[schema_name]
    validator = Draft202012Validator(schema, registry=_REGISTRY)
    return [e.message for e in validator.iter_errors(instance)]