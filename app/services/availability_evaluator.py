from dataclasses import dataclass
from datetime import datetime

from app.services import restriction_evaluator, unavailability_evaluator


@dataclass(frozen=True)
class AvailabilityEvaluation:
    allowed: bool
    decision: str
    considered_unavailabilities: list
    considered_restrictions: list
    applicable_unavailabilities: list
    applicable_restrictions: list
    reason: str
    interval_start: datetime
    interval_end: datetime
    priority: str
    explanation: str


def evaluate_service_interval(
    military_id: int,
    service_start: datetime,
    service_end: datetime,
) -> AvailabilityEvaluation:
    unavailability_result = unavailability_evaluator.evaluate_service_interval(
        military_id,
        service_start,
        service_end,
    )
    restriction_result = restriction_evaluator.evaluate_service_interval(
        military_id,
        service_start,
        service_end,
    )

    if not unavailability_result.allowed:
        return AvailabilityEvaluation(
            allowed=False,
            decision=unavailability_result.decision,
            considered_unavailabilities=unavailability_result.considered_unavailabilities,
            considered_restrictions=restriction_result.considered_restrictions,
            applicable_unavailabilities=unavailability_result.applicable_unavailabilities,
            applicable_restrictions=[],
            reason=unavailability_result.reason,
            interval_start=service_start,
            interval_end=service_end,
            priority="UNAVAILABILITY",
            explanation="A indisponibilidade concreta confirmada prevalece sobre restrições individuais.",
        )

    if not restriction_result.allowed:
        return AvailabilityEvaluation(
            allowed=False,
            decision=restriction_result.decision,
            considered_unavailabilities=unavailability_result.considered_unavailabilities,
            considered_restrictions=restriction_result.considered_restrictions,
            applicable_unavailabilities=[],
            applicable_restrictions=restriction_result.applicable_restrictions,
            reason=restriction_result.reason,
            interval_start=service_start,
            interval_end=service_end,
            priority=restriction_result.priority,
            explanation="Não há indisponibilidade confirmada; aplica-se a avaliação das restrições individuais.",
        )

    return AvailabilityEvaluation(
        allowed=True,
        decision="ALLOWED",
        considered_unavailabilities=unavailability_result.considered_unavailabilities,
        considered_restrictions=restriction_result.considered_restrictions,
        applicable_unavailabilities=[],
        applicable_restrictions=restriction_result.applicable_restrictions,
        reason="O intervalo não é bloqueado por indisponibilidades nem por restrições.",
        interval_start=service_start,
        interval_end=service_end,
        priority="NO_BLOCK",
        explanation="A avaliação combinada terminou sem bloqueios.",
    )
