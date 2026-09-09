"""Suitability evaluation (PRD sections 46, 54).

Evaluates a sensor against an application profile's requirements.
Produces a SuitabilityResult with per-criterion pass/fail and overall classification.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..models.application_profile import (
    ApplicationProfile,
    CriterionResult,
    SuitabilityResult,
)
from ..models.common import Suitability
from ..simulation.monte_carlo import MonteCarloResult


@dataclass
class SuitabilityEvaluation:
    """Full suitability evaluation with traceable criteria."""

    suitability: Suitability
    criteria: List[CriterionResult]
    limitations: List[str]
    profile_id: str
    profile_name: str


def evaluate_suitability(
    profile: ApplicationProfile,
    mc_result: MonteCarloResult,
    range_uncertainty: float = 0.0,
    geometric_coverage: float = 0.0,
    has_insufficient_data: bool = False,
) -> SuitabilityEvaluation:
    """Evaluate sensor suitability against an application profile.

    PRD section 46: Classification must be traceable to explicit criteria.
    It shall not be generated solely by an LLM opinion.
    """
    criteria: List[CriterionResult] = []
    limitations: List[str] = []
    all_pass = True
    any_fail = False

    # Detection probability criterion
    threshold = profile.requirements.minimum_detection_probability
    met = mc_result.p_detected >= threshold
    criteria.append(CriterionResult(
        criterion="minimum_detection_probability",
        required=threshold,
        measured=mc_result.p_detected,
        passed=met,
    ))
    if not met:
        all_pass = False
        any_fail = True

    # Reliable detection criterion
    threshold = profile.requirements.minimum_reliable_probability
    met = mc_result.p_reliable >= threshold
    criteria.append(CriterionResult(
        criterion="minimum_reliable_probability",
        required=threshold,
        measured=mc_result.p_reliable,
        passed=met,
    ))
    if not met:
        all_pass = False
        any_fail = True

    # Range uncertainty criterion
    threshold = profile.requirements.maximum_range_uncertainty
    met = range_uncertainty <= threshold
    criteria.append(CriterionResult(
        criterion="maximum_range_uncertainty",
        required=threshold,
        measured=range_uncertainty,
        passed=met,
    ))
    if not met:
        all_pass = False
        any_fail = True

    # Geometric coverage criterion
    threshold = profile.requirements.minimum_coverage
    met = geometric_coverage >= threshold
    criteria.append(CriterionResult(
        criterion="minimum_coverage",
        required=threshold,
        measured=geometric_coverage,
        passed=met,
    ))
    if not met:
        all_pass = False
        any_fail = True

    # Insufficient data check
    if has_insufficient_data:
        limitations.append("Insufficient data for reliable estimation.")
        return SuitabilityEvaluation(
            suitability=Suitability.INSUFFICIENT_DATA,
            criteria=criteria,
            limitations=limitations,
            profile_id=profile.profile_id,
            profile_name=profile.name,
        )

    # Overall classification
    if all_pass:
        suitability = Suitability.SUITABLE
    elif any_fail:
        suitability = Suitability.NOT_SUITABLE
    else:
        suitability = Suitability.CONDITIONALLY_SUITABLE

    return SuitabilityEvaluation(
        suitability=suitability,
        criteria=criteria,
        limitations=limitations,
        profile_id=profile.profile_id,
        profile_name=profile.name,
    )


def to_suitability_result(eval: SuitabilityEvaluation) -> SuitabilityResult:
    """Convert evaluation to a SuitabilityResult model instance."""
    return SuitabilityResult(
        classification=eval.suitability,
        criteria=eval.criteria,
        limitations=eval.limitations,
    )