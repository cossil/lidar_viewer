"""Datasheet ingestion (SCHEMAS section 14, POST /datasheets/extract)."""

import json
import re
import secrets

from ..models.sensor import Sensor
from .datasheet_validator import EXTRACTIONS

PARAM_SPECS = [
    {"path": "sensor_id", "label": "Sensor ID", "id": "sensor_id"},
    {"path": "manufacturer", "label": "Manufacturer", "id": "manufacturer"},
    {"path": "model", "label": "Model", "id": "model"},
    {"path": "version", "label": "Version", "id": "version"},
    {"path": "sensor_type", "label": "Sensor type", "id": "sensor_type"},
    {"path": "scan_type", "label": "Scan type", "id": "scan_type"},
    {"path": "range.maximum", "label": "Maximum range", "id": "range_max", "unit": "m"},
    {"path": "range.minimum", "label": "Minimum range", "id": "range_min", "unit": "m"},
    {"path": "beam.horizontal_divergence", "label": "Beam divergence", "id": "beam_hdiv", "unit": "mrad"},
    {"path": "beam.vertical_divergence", "label": "Vertical divergence", "id": "beam_vdiv", "unit": "mrad"},
    {"path": "beam.beam_shape", "label": "Beam shape", "id": "beam_shape"},
    {"path": "scan.point_rate", "label": "Point rate", "id": "point_rate", "unit": "Hz"},
    {"path": "scan.rotation_frequency", "label": "Rotation frequency", "id": "rotation_frequency", "unit": "Hz"},
    {"path": "scan.frame_rate", "label": "Frame rate", "id": "frame_rate", "unit": "Hz"},
    {"path": "accuracy.range", "label": "Range accuracy", "id": "acc_range", "unit": "m"},
    {"path": "validation_status", "label": "Validation status", "id": "validation_status"},
]

STRING_IDS = {"sensor_id", "manufacturer", "model", "version",
                "sensor_type", "scan_type", "beam_shape", "validation_status"}

LINE_LABELS = {
    "sensor_id": "Sensor ID",
    "manufacturer": "Manufacturer",
    "model": "Model",
    "version": "Version",
    "sensor_type": "Sensor type",
    "scan_type": "Scan type",
    "range_max": "Maximum range",
    "range_min": "Minimum range",
    "beam_hdiv": "Beam divergence",
    "beam_vdiv": "Vertical divergence",
    "beam_shape": "Beam shape",
    "point_rate": "Point rate",
    "rotation_frequency": "Rotation frequency",
    "frame_rate": "Frame rate",
    "acc_range": "Range accuracy",
    "validation_status": "Validation status",
}

_INVIS = re.compile(r"[\u200b-\u200f\u2060-\u2061\u00ad\u3000\u27e6-\u27ed\ufe0f\uFEFF\u200e\u200f]")


def _clean(text):
    return _INVIS.sub("", text)


def _unknown(raw):
    if raw is None:
        return True
    if isinstance(raw, dict):
        if raw.get("status") in ("unknown", "not_identified"):
            return True
        if "value" in raw:
            return raw["value"] is None
        return False
    if isinstance(raw, str):
        return raw.strip().lower() in ("", "unknown", "n/a", "none", "not found")
    return False


def _scalar(raw):
    if isinstance(raw, dict):
        for key in ("value", "maximum", "minimum", "default"):
            if key in raw and raw[key] is not None:
                return raw[key]
        return None
    return raw


def _unit(raw, default=None):
    if isinstance(raw, dict):
        u = raw.get("unit")
        if isinstance(u, str) and u.strip():
            return u.strip()
    return default


def _set(target, path, value):
    parts = path.split(".")
    node = target
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def _get(data, ident, path):
    if ident in data:
        return data[ident]
    node = data
    for part in path.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


def _candidate_from_dict(data, warnings):
    candidate = {}
    for spec in PARAM_SPECS:
        raw = _get(data, spec["id"], spec["path"])
        if raw is None or _unknown(raw):
            warnings.append(spec["label"] + " was not identified.")
            continue
        val = _scalar(raw)
        if val is None or (isinstance(val, str) and not val.strip()):
            warnings.append(spec["label"] + " was not identified.")
            continue
        if spec["id"] in STRING_IDS:
            _set(candidate, spec["path"], val)
        else:
            value_block = {"value": val, "unit": _unit(raw, spec.get("unit"))}
            _set(candidate, spec["path"], value_block)
    return candidate


_NUM = re.compile(r"^\s*([-+0-9,  .]+?)\s*([A-Za-zµ%/°]*?)\s*$")


def _line_parse(text):
    parsed = {}
    for raw_line in text.splitlines():
        line = _clean(raw_line).strip(" \t:")
        if not line or ":" not in line:
            continue
        header, _sep, rest = line.partition(":")
        header = header.strip()
        rest = rest.strip()
        if not header or not rest:
            continue
        for ident, label in LINE_LABELS.items():
            if header.lower() != label.lower():
                continue
            if ident in parsed:
                break
            m = _NUM.match(rest)
            if m:
                num_txt = m.group(1).replace(",", "").replace(" ", "")
                try:
                    num = float(num_txt)
                except ValueError:
                    num = None
                if num is not None:
                    parsed[ident] = {"value": num, "unit": m.group(2) or None}
                else:
                    parsed[ident] = {"value": rest, "unit": None}
            else:
                parsed[ident] = {"value": rest, "unit": None}
            break
    return parsed


def _candidate_from_text(text, warnings):
    parsed = _line_parse(text)
    candidate = {}
    for spec in PARAM_SPECS:
        raw = parsed.get(spec["id"])
        if raw is None or _unknown(raw):
            warnings.append(spec["label"] + " was not identified.")
            continue
        val = _scalar(raw)
        if val is None or (isinstance(val, str)and not val.strip()):
            warnings.append(spec["label"] + " was not identified.")
            continue
        if spec["id"] in STRING_IDS:
            _set(candidate, spec["path"], val)
        else:
            value_block = {"value": val, "unit": _unit(raw, spec.get("unit"))}
            _set(candidate, spec["path"], value_block)
    return candidate


def _reconstruct(candidate):
    if not candidate:
        return None
    try:
        return Sensor.model_validate(candidate)
    except Exception:
        return None


def ingest_datasheet(
    data=None,
    filename="",
    content_type="application/json",
    use_llm: bool = False,
    llm_model: str = "z-ai/glm-5.3-flash",
):
    ctype = (content_type or "").lower()
    warnings = []
    if data is None:
        data = {}

    candidate = {}
    if use_llm:
        from .llm_extractor import extract_with_openrouter
        try:
            raw_text = data if isinstance(data, str) else (json.dumps(data) if isinstance(data, dict) else str(data))
            llm_result = extract_with_openrouter(raw_text, model=llm_model)
            candidate = _candidate_from_dict(llm_result, warnings)
        except Exception as e:
            warnings.append(f"LLM extraction error ({e}); falling back to standard parser.")
            use_llm = False

    if not candidate:
        if ("json" in ctype) or isinstance(data, dict):
            candidate = _candidate_from_dict(data, warnings)
        elif any(tok in ctype for tok in ("pdf", "text", "txt", "plain")):
            candidate = _candidate_from_text(data if isinstance(data, str) else "", warnings)
        else:
            candidate = _candidate_from_dict(data if isinstance(data, dict) else {}, warnings)

    built = _reconstruct(candidate)
    if built is not None:
        candidate = built
    else:
        warnings.append("Sensor object incomplete - requires manual completion")
    result = {
        "extraction_id": "ext_" + secrets.token_hex(4),
        "status": "completed",
        "sensor_candidate": candidate,
        "warnings": warnings,
        "llm_used": use_llm,
        "llm_model": llm_model if use_llm else None,
    }
    EXTRACTIONS[result["extraction_id"]] = result
    return result