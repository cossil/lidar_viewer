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


def compute_parametric_range_noise(
    d: float,
    sigma_min: float,
    sigma_max: float,
    d_max: float,
) -> float:
    """Parametric Range Noise Model (Generalized Exponential).

    sigma(d) = sigma_min * (sigma_max / sigma_min) ** (d / d_max)

    Input Parameters:
    - d (float): Current measurement distance (m).
    - sigma_min (float): Minimum standard deviation / base noise floor at d=0 (m).
    - sigma_max (float): Standard deviation at maximum sensor range d_max (m).
    - d_max (float): Maximum operating range of sensor under 10% Lambertian reflectivity (m).

    Rules:
    - If d < 0: return sigma_min (treat as d = 0.0).
    - If d > d_max: return sigma_max (saturation / out-of-range clamp).
    - Guard sigma_min > 0 and sigma_max >= sigma_min to prevent zero divisions or negative ratios.
    """
    if sigma_min <= 0.0:
        sigma_min = 1e-6
    if sigma_max < sigma_min:
        sigma_max = sigma_min
    if d_max <= 0.0:
        return float(sigma_min)

    if d <= 0.0:
        return float(sigma_min)
    if d >= d_max:
        return float(sigma_max)

    ratio = sigma_max / sigma_min
    exponent = d / d_max
    return float(sigma_min * (ratio ** exponent))


@dataclass
class MeasurementConfig:
    """Configuration for a single measurement axis."""

    bias: float = 0.0
    sigma: float = 0.0
    error_definition: ErrorDefinition = ErrorDefinition.ONE_SIGMA
    sigma_min: Optional[float] = None
    sigma_max: Optional[float] = None
    d_max: Optional[float] = None

    def get_sigma(self, distance: Optional[float] = None) -> float:
        """Resolve standard deviation, using parametric model if configured."""
        if (
            distance is not None
            and self.sigma_min is not None
            and self.sigma_max is not None
            and self.d_max is not None
            and self.d_max > 0
        ):
            return compute_parametric_range_noise(
                d=distance,
                sigma_min=self.sigma_min,
                sigma_max=self.sigma_max,
                d_max=self.d_max,
            )
        return self.sigma


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
        range_sigma = self.range_config.get_sigma(true_range)
        range_noise = rng.normal(0, range_sigma)
        angle_noise_h = rng.normal(0, self.angular_config.get_sigma(true_range))
        angle_noise_v = rng.normal(0, self.angular_config.get_sigma(true_range))

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