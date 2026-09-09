"""Scan engine: generates candidate ray directions from sensor scanning geometry.

PRD sections 20-24.
"""

from .scanners import (
    Channel,
    MechanicalSpinningScanner,
    NonRepetitiveScanner,
    ScanModel,
    ScanPoint,
    StructuredRasterScanner,
)

__all__ = [
    "ScanModel",
    "ScanPoint",
    "Channel",
    "MechanicalSpinningScanner",
    "StructuredRasterScanner",
    "NonRepetitiveScanner",
]