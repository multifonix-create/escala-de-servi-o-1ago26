from dataclasses import dataclass
from datetime import datetime, time, timedelta

from app.models import Unavailability
from app.services import unavailability_service


@dataclass(frozen=True)
class UnavailabilityInterval:
    unavailability: Unavailability
    start: datetime
    end: datetime
    effective_start: datetime
    effective_end: datetime


@dataclass(frozen=True)
class UnavailabilityEvaluation:
    allowed: bool
    decision: str
    considered_unavailabilities: list[Unavailability]
    applicable_unavailabilities: list[Unavailability]
    reason: str
    priority: str
    conflict: bool
    interval_start: datetime
    interval_end: datetime


def evaluate_service_interval(
    military_id: int,
    service_start: datetime,
    service_end: datetime,
) -> UnavailabilityEvaluation:
    if service_end <= service_start:
        raise ValueError("O fim do serviço deve ser posterior ao início.")

    considered = unavailability_service.list_blocking_unavailabilities_for_interval(
        military_id,
        service_start,
        service_end,
    )
    applicable = []
    for unavailability in considered:
        interval = interval_for_unavailability(unavailability)
        if overlaps(interval.effective_start, interval.effective_end, service_start, service_end):
            applicable.append(unavailability)

    if applicable:
        return UnavailabilityEvaluation(
            allowed=False,
            decision="BLOCKED_BY_UNAVAILABILITY",
            considered_unavailabilities=considered,
            applicable_unavailabilities=applicable,
            reason="Existe indisponibilidade confirmada sobreposta ao intervalo.",
            priority="UNAVAILABILITY",
            conflict=True,
            interval_start=service_start,
            interval_end=service_end,
        )

    return UnavailabilityEvaluation(
        allowed=True,
        decision="ALLOWED",
        considered_unavailabilities=considered,
        applicable_unavailabilities=[],
        reason="Não existem indisponibilidades confirmadas que bloqueiem o intervalo.",
        priority="NO_UNAVAILABILITY",
        conflict=False,
        interval_start=service_start,
        interval_end=service_end,
    )


def interval_for_unavailability(unavailability: Unavailability) -> UnavailabilityInterval:
    start, end = raw_interval_for_unavailability(unavailability)
    effective_start = start - timedelta(minutes=unavailability.travel_minutes_before)
    effective_end = end + timedelta(minutes=unavailability.travel_minutes_after)
    return UnavailabilityInterval(
        unavailability=unavailability,
        start=start,
        end=end,
        effective_start=effective_start,
        effective_end=effective_end,
    )


def raw_interval_for_unavailability(unavailability: Unavailability) -> tuple[datetime, datetime]:
    if unavailability.is_full_day:
        return (
            datetime.combine(unavailability.start_date, time.min),
            datetime.combine(unavailability.end_date + timedelta(days=1), time.min),
        )

    start = datetime.combine(unavailability.start_date, unavailability.start_time)
    end_date = unavailability.end_date
    if unavailability.end_date == unavailability.start_date and unavailability.end_time <= unavailability.start_time:
        end_date = unavailability.end_date + timedelta(days=1)
    end = datetime.combine(end_date, unavailability.end_time)
    return start, end


def overlaps(first_start: datetime, first_end: datetime, second_start: datetime, second_end: datetime) -> bool:
    return first_start < second_end and second_start < first_end
