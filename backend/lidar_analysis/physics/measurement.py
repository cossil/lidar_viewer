"""Measurement model (PRD sections 33-34).

Measured range: R_m = R_t + b_R + ε_R, where ε_R ~ N(0, σ_R²)
Measured angle: θ_m = θ_t + b_θ + ε_θ

Error definitions (PRD section 34): 1sigma, 2sigma, 95_percent, rms, maximum, unspecified.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from ..models.common import ErrorDefinition


@dataclass
class MeasurementConfig:
    """Configuration for a single measurement axis."""

    bias: float = 0.0
    sigma: float = 0.0
    error_definition: ErrorDefinition = ErrorDefinition.ONE_SIGMA


@dataclass
class MeasurementSample:
    """A single noisy measurement."""

    measured_range: float
    measured_angle_h: float
    measured_angle_v: float
    true_range: float
    true_angle_h: float
    true_angle_v: float


class MeasurementModel:
    """Applies systematic bias and random noise to true measurements.

    PRD section 33: R_m = R_t + b_R + ε_R
    PRD section 34: sigma definition must be explicitly recorded.
    """

    def __init__(
        self,
        range_config: MeasurementConfig,
        angular_config: MeasurementConfig,
    ):
        self.range_config = range_config
        self.angular_config = angular_config

    def apply(
        self,
        true_range: float,
        true_angle_h: float,
        true_angle_v: float,
        rng: np.random.Generator,
    ) -> MeasurementSample:
        """Apply measurement error to a true observation.

        Args:
            true_range: True range in meters.
            true_angle_h: True horizontal angle in radians.
            true_angle_v: True vertical angle in radians.
            rng: Random number generator for reproducibility.

        Returns:
            MeasurementSample with noisy measurements.
        """
        range_noise = rng.normal(0, self.range_config.sigma)
        angle_noise_h = rng.normal(0, self.angular_config.sigma)
        angle_noise_v = rng.normal(0, self.angular_config.sigma)

        return MeasurementSample(
            measured_range=true_range + self.range_config.bias + range_noise,
            measured_angle_h=true_angle_h + self.angular_config.bias + angle_noise_h,
            measured_angle_v=true_angle_v + self.angular_config.bias + angle_noise_v,
            true_range=true_range,
            true_angle_h=true_angle_h,
            true_angle_v=true_angle_v,
        )


def convert_sigma(
    sigma: float,
    from_def: ErrorDefinition,
    to_def: ErrorDefinition,
) -> float:
    """Convert sigma between error definitions (PRD section 34).

    Only converts between 1sigma, 2sigma, and 95_percent (Gaussian assumption).
    """
    if from_def == to_def:
        return sigma

    # Convert to 1sigma first
    if from_def == ErrorDefinition.ONE_SIGMA:
        s1 = sigma
    elif from_def == ErrorDefinition.TWO_SIGMA:
        s1 = sigma / 2.0
    elif from_def == ErrorDefinition.PERCENT_95:
        s1 = sigma / 1.96
    else:
        raise ValueError(f"Cannot convert from {from_def}")

    # Convert from 1sigma to target
    if to_def == ErrorDefinition.ONE_SIGMA:
        return s1
    elif to_def == ErrorDefinition.TWO_SIGMA:
        return s1 * 2.0
    elif to_def == ErrorDefinition.PERCENT_95:
        return s1 * 1.96
    else:
        raise ValueError(f"Cannot convert to {to_def}")