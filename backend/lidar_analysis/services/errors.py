"""Standard API error contract (SCHEMAS sec 25).

Recommended error codes from the spec are exposed as constants so the whole app
uses one vocabulary. The wire shape is exactly:
{"error": {"code", "message", "field", "details"}}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ERROR_CODES = {
    "INVALID_PARAMETER",
    "MISSING_PARAMETER",
    "INVALID_UNIT",
    "UNKNOWN_SENSOR",
    "UNKNOWN_SCENARIO",
    "UNKNOWN_SIMULATION",
    "INVALID_GEOMETRY",
    "INVALID_DETECTION_MODEL",
    "INSUFFICIENT_DATA",
    "SIMULATION_NOT_COMPLETE",
    "SIMULATION_FAILED",
    "INTERNAL_ERROR",
}

# Individual constants for convenience
INVALID_PARAMETER = "INVALID_PARAMETER"
MISSING_PARAMETER = "MISSING_PARAMETER"
INVALID_UNIT = "INVALID_UNIT"
UNKNOWN_SENSOR = "UNKNOWN_SENSOR"
UNKNOWN_SCENARIO = "UNKNOWN_SCENARIO"
UNKNOWN_SIMULATION = "UNKNOWN_SIMULATION"
INVALID_GEOMETRY = "INVALID_GEOMETRY"
INVALID_DETECTION_MODEL = "INVALID_DETECTION_MODEL"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
SIMULATION_NOT_COMPLETE = "SIMULATION_NOT_COMPLETE"
SIMULATION_FAILED = "SIMULATION_FAILED"
INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class ApiError(Exception):
    """Raised by services; caught by the API layer and converted to the standard body.

    """

    code: str = INTERNAL_ERROR
    message: str = ""
    field: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    http_status: int = 400

    def body(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.field is not None:
            payload["field"] = self.field
        if self.details:
            payload["details"] = self.details
        return {"error": payload}


def error_response(code: str, message: str, field: str | None = None, details: dict | None = None, http_status: int = 400) -> ApiError:
    return ApiError(code=code, message=message, field=field, details=(details or {}), http_status=http_status)

def insufficient_data(missing_parameters: list[str], message: str | None = None) -> ApiError:
    """SCHEMAS sec 27 Insufficient Data Response."""
    return ApiError(
        code=INSUFFICIENT_DATA,
        message=message or "The selected detection model requires a parameter that the sensor model does not contain a validated value.",
        details={"missing_parameters": missing_parameters},
        http_status=422,
    )

def not_complete(status: str = "running") -> ApiError:
    """SCHEMAS sec 19: 409 Conflict body."""
    return ApiError(
        code=SIMULATION_NOT_COMPLETE,
        message="simulation_not_complete",
        details={"status": status},
        http_status=409,
    )