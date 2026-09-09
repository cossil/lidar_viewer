# Datasheet validation (SCHEMAS section 15).
# Resolves an extraction, derives version, and reports the validation status.
# An empty validated_parameters yields needs_review; an unknown extraction id
# raises KeyError.


EXTRACTIONS = {}


def validate_datasheet(extraction_id, validated_parameters=None, store=None):
    registry = store if store is not None else EXTRACTIONS
    if extraction_id not in registry:
        raise KeyError("unknown extraction id: %s" % extraction_id)
    candidate = registry[extraction_id].get("sensor_candidate", {})
    params = validated_parameters if validated_parameters is not None else {}
    version = None
    if isinstance(candidate, dict):
        version = candidate.get("version")
    if not version:
        version = params.get("version")
        if isinstance(version, dict):
            version = version.get("value")
    if version is None:
        version = "1.0"
    sensor_id = None
    if isinstance(candidate, dict):
        sensor_id = candidate.get("sensor_id")
    if not sensor_id:
        sensor_id = "sensor_%s" % extraction_id[4:]
    status = "needs_review" if not params else "validated"
    return {
        "sensor_id": sensor_id,
        "version": version,
        "validation_status": status,
    }


def clear_extractions():
    """Remove all stored extractions from the module-level registry (test helper)."""
    EXTRACTIONS.clear()