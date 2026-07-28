from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from app.models import MilitaryRestriction, RestrictionType
from app.services import restriction_service


@dataclass(frozen=True)
class RestrictionInterval:
    restriction: MilitaryRestriction
    start: datetime
    end: datetime


@dataclass(frozen=True)
class RestrictionEvaluation:
    allowed: bool
    decision: str
    considered_restrictions: list[MilitaryRestriction]
    applicable_restrictions: list[MilitaryRestriction]
    reason: str
    priority: str
    conflict: bool
    has_special_availability: bool


def evaluate_service_interval(
    military_id: int,
    service_start: datetime,
    service_end: datetime,
) -> RestrictionEvaluation:
    if service_end <= service_start:
        raise ValueError("O fim do serviço deve ser posterior ao início.")

    considered = _active_restrictions_for_interval(military_id, service_start, service_end)
    unavailable_matches = []
    available_intervals = []
    special_intervals = []

    for restriction in considered:
        intervals = intervals_for_restriction(restriction, service_start, service_end)
        if restriction.restriction_type == RestrictionType.UNAVAILABLE.value:
            unavailable_matches.extend(
                interval for interval in intervals if overlaps(interval.start, interval.end, service_start, service_end)
            )
        elif restriction.restriction_type == RestrictionType.AVAILABLE_ONLY.value:
            available_intervals.extend(intervals)
        elif restriction.restriction_type == RestrictionType.SPECIAL_AVAILABILITY.value:
            special_intervals.extend(intervals)

    if unavailable_matches:
        return RestrictionEvaluation(
            allowed=False,
            decision="BLOCKED",
            considered_restrictions=considered,
            applicable_restrictions=[interval.restriction for interval in unavailable_matches],
            reason="Existe uma restrição absoluta sobreposta ao intervalo.",
            priority="UNAVAILABLE",
            conflict=True,
            has_special_availability=bool(special_intervals),
        )

    if any(contains(interval.start, interval.end, service_start, service_end) for interval in special_intervals):
        return RestrictionEvaluation(
            allowed=True,
            decision="ALLOWED_BY_SPECIAL_AVAILABILITY",
            considered_restrictions=considered,
            applicable_restrictions=[interval.restriction for interval in special_intervals],
            reason="O serviço está integralmente contido numa disponibilidade especial.",
            priority="SPECIAL_AVAILABILITY",
            conflict=False,
            has_special_availability=True,
        )

    if _has_available_only_restriction_active_for_interval(considered):
        if any(contains(interval.start, interval.end, service_start, service_end) for interval in available_intervals):
            return RestrictionEvaluation(
                allowed=True,
                decision="ALLOWED_BY_AVAILABLE_ONLY",
                considered_restrictions=considered,
                applicable_restrictions=[interval.restriction for interval in available_intervals],
                reason="O serviço está integralmente contido numa janela autorizada.",
                priority="AVAILABLE_ONLY",
                conflict=False,
                has_special_availability=bool(special_intervals),
            )
        return RestrictionEvaluation(
            allowed=False,
            decision="BLOCKED_OUTSIDE_AVAILABLE_ONLY",
            considered_restrictions=considered,
            applicable_restrictions=[
                restriction
                for restriction in considered
                if restriction.restriction_type == RestrictionType.AVAILABLE_ONLY.value
            ],
            reason="Existe disponibilidade limitada e o serviço não está contido numa janela autorizada.",
            priority="MOST_RESTRICTIVE",
            conflict=True,
            has_special_availability=bool(special_intervals),
        )

    return RestrictionEvaluation(
        allowed=True,
        decision="ALLOWED",
        considered_restrictions=considered,
        applicable_restrictions=[],
        reason="Não existem restrições que bloqueiem o intervalo.",
        priority="NO_RESTRICTION",
        conflict=False,
        has_special_availability=bool(special_intervals),
    )


def intervals_for_restriction(
    restriction: MilitaryRestriction,
    service_start: datetime,
    service_end: datetime,
) -> list[RestrictionInterval]:
    intervals = []
    current = service_start.date() - timedelta(days=1)
    last_date = service_end.date()
    while current <= last_date:
        if _occurrence_is_valid(restriction, current):
            interval_start, interval_end = _build_occurrence_interval(restriction, current)
            if overlaps(interval_start, interval_end, service_start, service_end) or contains(
                interval_start,
                interval_end,
                service_start,
                service_end,
            ):
                intervals.append(
                    RestrictionInterval(
                        restriction=restriction,
                        start=interval_start,
                        end=interval_end,
                    )
                )
        current += timedelta(days=1)
    return intervals


def overlaps(first_start: datetime, first_end: datetime, second_start: datetime, second_end: datetime) -> bool:
    return first_start < second_end and second_start < first_end


def contains(container_start: datetime, container_end: datetime, item_start: datetime, item_end: datetime) -> bool:
    return container_start <= item_start and item_end <= container_end


def _active_restrictions_for_interval(
    military_id: int,
    service_start: datetime,
    service_end: datetime,
) -> list[MilitaryRestriction]:
    restrictions = []
    current = service_start.date() - timedelta(days=1)
    last_date = service_end.date()
    seen_ids = set()
    while current <= last_date:
        for restriction in restriction_service.get_active_restrictions_for_military_on_date(
            military_id,
            current,
        ):
            if restriction.id not in seen_ids:
                restrictions.append(restriction)
                seen_ids.add(restriction.id)
        current += timedelta(days=1)
    return sorted(restrictions, key=lambda item: item.id)


def _has_available_only_restriction_active_for_interval(
    restrictions: list[MilitaryRestriction],
) -> bool:
    return any(
        restriction.restriction_type == RestrictionType.AVAILABLE_ONLY.value
        for restriction in restrictions
    )


def _occurrence_is_valid(restriction: MilitaryRestriction, occurrence_date: date) -> bool:
    if occurrence_date < restriction.start_date:
        return False
    if restriction.end_date and occurrence_date > restriction.end_date:
        return False
    return restriction.applies_to_weekday(occurrence_date.weekday())


def _build_occurrence_interval(
    restriction: MilitaryRestriction,
    occurrence_date: date,
) -> tuple[datetime, datetime]:
    if restriction.is_full_day:
        return (
            datetime.combine(occurrence_date, time.min),
            datetime.combine(occurrence_date + timedelta(days=1), time.min),
        )
    interval_start = datetime.combine(occurrence_date, restriction.start_time)
    end_date = occurrence_date + timedelta(days=1) if restriction.crosses_midnight else occurrence_date
    interval_end = datetime.combine(end_date, restriction.end_time)
    return interval_start, interval_end
