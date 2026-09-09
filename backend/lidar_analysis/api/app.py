"""FastAPI application — LiDAR Performance Analysis Platform.

PRD section 58: REST API for sensors, scenarios, simulations, analysis.
"""

from __future__ import annotations

from fastapi import FastAPI

from .errors import register_error_handlers
from .routes import sensors, scenarios, simulations, analysis, reports, datasheets


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="LiDAR Performance Analysis Platform",
        version="0.1.0",
        description="Monte Carlo LiDAR simulation and analysis API",
    )

    app.include_router(sensors.router, prefix="/api/sensors", tags=["sensors"])
    app.include_router(scenarios.router, prefix="/api/scenarios", tags=["scenarios"])
    app.include_router(simulations.router, prefix="/api/simulations", tags=["simulations"])
    app.include_router(analysis.router, prefix="/api/analysis", tags=["analysis"])
    app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
    app.include_router(datasheets.router, prefix="/api/datasheets", tags=["datasheets"])

    register_error_handlers(app)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()