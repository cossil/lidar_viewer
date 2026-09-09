"""Standard API error envelope (PRD section 25.

All errors are returned as::

    {"error": {"code": str, "message": str, "field": str | None, "details": {}}}

Recommended error codes:
INVALID_PARAMETER, MISSING_PARAMETER, INVALID_UNIT, UNKNOWN_SENSOR,
UNKNOWN_SCENARIO, UNKNOWN_SIMULATION, INVALID_GEOMETRY,
INVALID_DETECTION_MODEL, INSUFFICIENT_DATA, SIMULATION_NOT_COMPLETE,
SIMULATION_FAILED, INTERNAL_ERROR.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class ApiError(Exception):
    """Raise inside route handlers to surface a standard error envelope."""

    def __init__(
        self,
        status_code: int = 400,
        code: str = "INVALID_PARAMETER",
        message: str = "An error occurred.",
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.field = field
        self.details = details or {}


def api_error(
    request: Request, exc: Exception, status_code: int | None = None
) -> JSONResponse:
    """Build the standard error envelope response for an exception."""
    code = "INTERNAL_ERROR"
    message = str(exc) or "Internal server error."
    field: Optional[str] = None
    details: Dict[str, Any] = {}
    effective_status = status_code or 500

    if isinstance(exc, ApiError):
        code = exc.code
        message = exc.message or message
        field = exc.field
        details = exc.details or {}
        effective_status = status_code or exc.status_code

    return JSONResponse(
        status_code=effective_status,
        content={
            "error": {
                "code": code,
                "message": message,
                "field": field,
                "details": details,
            }
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    """Wire the standard error handler(s) onto the app (PRD §25)."""
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(ApiError)
    async def _handle_api_error(request: Request, exc: ApiError) -> JSONResponse:
        return api_error(request, exc)

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "INTERNAL_ERROR"
        field = None
        details: Dict[str, Any] = {}
        msg = str(exc.detail) if exc.detail else "An error occurred."
        msg_lower = msg.lower()

        if exc.status_code == 404:
            if "sensor" in msg_lower:
                code = "UNKNOWN_SENSOR"
                field = "sensor_id"
            elif "scenario" in msg_lower:
                code = "UNKNOWN_SCENARIO"
                field = "scenario_id"
            elif "simulation" in msg_lower:
                code = "UNKNOWN_SIMULATION"
                field = "simulation_id"
            elif "report" in msg_lower:
                code = "UNKNOWN_REPORT"
                field = "report_id"
            else:
                code = "NOT_FOUND"
        elif exc.status_code == 422:
            code = "INVALID_PARAMETER"
        elif exc.status_code == 400:
            code = "INVALID_PARAMETER"
        elif exc.status_code == 409:
            code = "SIMULATION_NOT_COMPLETE"

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": msg,
                    "field": field,
                    "details": details,
                },
                "detail": msg,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        first_loc = errors[0].get("loc", []) if errors else []
        field = str(first_loc[-1]) if first_loc else None
        msg = errors[0].get("msg", "Validation error") if errors else "Validation error"
        code = "MISSING_PARAMETER" if "missing" in msg.lower() else "INVALID_PARAMETER"
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": code,
                    "message": f"Validation failed for field '{field}': {msg}",
                    "field": field,
                    "details": {"validation_errors": errors},
                },
                "detail": errors,
            },
        )

    @app.exception_handler(Exception)
    async def _handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
        msg = str(exc) or "Internal server error."
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": msg,
                    "field": None,
                    "details": {},
                },
                "detail": msg,
            },
        )