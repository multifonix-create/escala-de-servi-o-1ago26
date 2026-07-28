from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import or_

from app.extensions import db
from app.models import (
    CompensationStatus,
    FunctionalType,
    Military,
    Unavailability,
    UnavailabilityEvent,
    UnavailabilityEventType,
    UnavailabilityStatus,
    UNAVAILABILITY_LABELS,
)
from app.services import cycle_calculator, membership_service


class UnavailabilityServiceError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__("Dados de indisponibilidade inválidos.")
        self.errors = errors


@dataclass(frozen=True)
class CycleCoincidence:
    day: date
    code: str | None
    status: str
    detail: str


def list_unavailabilities(
    military_id: int | None = None,
    code: str | None = None,
    status: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Unavailability]:
    statement = Unavailability.query.join(Military)
    if military_id is not None:
        statement = statement.filter(Unavailability.military_id == military_id)
    if code:
        statement = statement.filter(Unavailability.code == code)
    if status:
        statement = statement.filter(Unavailability.status == status)
    if start_date:
        statement = statement.filter(Unavailability.end_date >= start_date)
    if end_date:
        statement = statement.filter(Unavailability.start_date <= end_date)
    return statement.order_by(Unavailability.start_date.desc(), Military.name.asc()).all()


def list_unavailabilities_for_military(military_id: int) -> list[Unavailability]:
    return (
        Unavailability.query.filter(Unavailability.military_id == military_id)
        .order_by(Unavailability.start_date.desc(), Unavailability.id.desc())
        .all()
    )


def count_future_unavailabilities_for_military(military_id: int, today: date | None = None) -> int:
    reference = today or date.today()
    return (
        Unavailability.query.filter(
            Unavailability.military_id == military_id,
            Unavailability.is_active.is_(True),
            Unavailability.status != UnavailabilityStatus.CANCELLED.value,
            Unavailability.end_date >= reference,
        ).count()
    )


def next_unavailability_for_military(military_id: int, today: date | None = None) -> Unavailability | None:
    reference = today or date.today()
    return (
        Unavailability.query.filter(
            Unavailability.military_id == military_id,
            Unavailability.is_active.is_(True),
            Unavailability.status != UnavailabilityStatus.CANCELLED.value,
            Unavailability.end_date >= reference,
        )
        .order_by(Unavailability.start_date.asc(), Unavailability.id.asc())
        .first()
    )


def get_unavailability_or_404(unavailability_id: int) -> Unavailability:
    return db.get_or_404(Unavailability, unavailability_id)


def create_unavailability(military: Military, data: dict) -> tuple[Unavailability, list[Unavailability]]:
    _raise_for_duplicate(military.id, data)
    overlaps = find_overlaps(military.id, data)
    unavailability = Unavailability(military_id=military.id, **data)
    try:
        db.session.add(unavailability)
        db.session.flush()
        _add_event(unavailability, UnavailabilityEventType.CREATED.value, None, unavailability.status, "Criação da indisponibilidade.")
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return unavailability, overlaps


def update_unavailability(unavailability: Unavailability, data: dict) -> tuple[Unavailability, list[Unavailability]]:
    _raise_for_duplicate(unavailability.military_id, data, excluded_id=unavailability.id)
    overlaps = find_overlaps(unavailability.military_id, data, excluded_id=unavailability.id)
    previous_status = unavailability.status
    try:
        for field, value in data.items():
            setattr(unavailability, field, value)
        db.session.flush()
        _add_event(unavailability, UnavailabilityEventType.UPDATED.value, previous_status, unavailability.status, "Edição da indisponibilidade.")
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return unavailability, overlaps


def confirm_unavailability(unavailability: Unavailability) -> Unavailability:
    if unavailability.status == UnavailabilityStatus.CANCELLED.value:
        raise UnavailabilityServiceError({"status": "Uma indisponibilidade cancelada exige reativação explícita antes de confirmar."})
    if unavailability.status == UnavailabilityStatus.CONFIRMED.value:
        return unavailability
    return _change_status(unavailability, UnavailabilityStatus.CONFIRMED.value, UnavailabilityEventType.CONFIRMED.value)


def cancel_unavailability(unavailability: Unavailability) -> Unavailability:
    if unavailability.status == UnavailabilityStatus.CANCELLED.value:
        return unavailability
    return _change_status(unavailability, UnavailabilityStatus.CANCELLED.value, UnavailabilityEventType.CANCELLED.value)


def reactivate_unavailability(unavailability: Unavailability) -> Unavailability:
    if unavailability.status != UnavailabilityStatus.CANCELLED.value:
        raise UnavailabilityServiceError({"status": "Apenas indisponibilidades canceladas podem ser reativadas."})
    return _change_status(unavailability, UnavailabilityStatus.PLANNED.value, UnavailabilityEventType.REACTIVATED.value)


def deactivate_unavailability(unavailability: Unavailability) -> Unavailability:
    unavailability.is_active = False
    db.session.commit()
    return unavailability


def list_blocking_unavailabilities_for_interval(military_id: int, start, end) -> list[Unavailability]:
    return (
        Unavailability.query.filter(
            Unavailability.military_id == military_id,
            Unavailability.is_active.is_(True),
            Unavailability.status == UnavailabilityStatus.CONFIRMED.value,
            Unavailability.start_date <= end.date(),
            Unavailability.end_date >= start.date() - timedelta(days=1),
        )
        .order_by(Unavailability.start_date.asc(), Unavailability.id.asc())
        .all()
    )


def find_overlaps(military_id: int, data: dict, excluded_id: int | None = None) -> list[Unavailability]:
    from app.services.unavailability_evaluator import interval_for_unavailability, overlaps

    probe = Unavailability(military_id=military_id, **data)
    probe_interval = interval_for_unavailability(probe)
    statement = Unavailability.query.filter(
        Unavailability.military_id == military_id,
        Unavailability.is_active.is_(True),
        Unavailability.status != UnavailabilityStatus.CANCELLED.value,
        Unavailability.start_date <= probe_interval.effective_end.date(),
        Unavailability.end_date >= probe_interval.effective_start.date(),
    )
    if excluded_id is not None:
        statement = statement.filter(Unavailability.id != excluded_id)
    matches = []
    for item in statement.order_by(Unavailability.start_date.asc(), Unavailability.id.asc()).all():
        item_interval = interval_for_unavailability(item)
        if overlaps(
            item_interval.effective_start,
            item_interval.effective_end,
            probe_interval.effective_start,
            probe_interval.effective_end,
        ):
            matches.append(item)
    return matches


def calculate_cycle_coincidences(military: Military, start_date: date, end_date: date) -> list[CycleCoincidence]:
    days = []
    current = start_date
    while current <= end_date:
        days.append(_cycle_coincidence_for_day(military, current))
        current += timedelta(days=1)
    return days


def format_code(code: str) -> str:
    return UNAVAILABILITY_LABELS.get(code, code)


def _cycle_coincidence_for_day(military: Military, target_date: date) -> CycleCoincidence:
    if military.functional_type != FunctionalType.PATRULHEIRO.value:
        return CycleCoincidence(target_date, None, "NOT_APPLICABLE", "Não aplicável ao tipo funcional.")
    team = membership_service.get_team_for_military_on_date(military.id, target_date)
    if team is None:
        return CycleCoincidence(target_date, None, "UNKNOWN", "Não foi possível determinar equipa válida.")
    try:
        cycle_day = cycle_calculator.calculate_team_day(team, target_date)
    except cycle_calculator.MissingTeamReferenceError:
        return CycleCoincidence(target_date, None, "UNKNOWN", "Não existe referência de ciclo válida.")
    if cycle_day.code in {"DS", "DC"}:
        return CycleCoincidence(target_date, cycle_day.code, "REST_DAY", f"Coincide com {cycle_day.code}.")
    return CycleCoincidence(target_date, None, "NO_REST", "Sem DS/DC nesta data.")


def _raise_for_duplicate(military_id: int, data: dict, excluded_id: int | None = None) -> None:
    statement = Unavailability.query.filter(
        Unavailability.military_id == military_id,
        Unavailability.code == data["code"],
        Unavailability.start_date == data["start_date"],
        Unavailability.end_date == data["end_date"],
        Unavailability.start_time.is_(data["start_time"]) if data["start_time"] is None else Unavailability.start_time == data["start_time"],
        Unavailability.end_time.is_(data["end_time"]) if data["end_time"] is None else Unavailability.end_time == data["end_time"],
        Unavailability.is_full_day == data["is_full_day"],
        Unavailability.status != UnavailabilityStatus.CANCELLED.value,
        Unavailability.is_active.is_(True),
    )
    if excluded_id is not None:
        statement = statement.filter(Unavailability.id != excluded_id)
    if db.session.query(statement.exists()).scalar():
        raise UnavailabilityServiceError({"code": "Já existe uma indisponibilidade igual para este militar."})


def _change_status(unavailability: Unavailability, new_status: str, event_type: str) -> Unavailability:
    previous_status = unavailability.status
    try:
        unavailability.status = new_status
        if new_status != UnavailabilityStatus.CANCELLED.value:
            unavailability.is_active = True
        _add_event(unavailability, event_type, previous_status, new_status, "Alteração de estado da indisponibilidade.")
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return unavailability


def _add_event(
    unavailability: Unavailability,
    event_type: str,
    previous_status: str | None,
    new_status: str | None,
    description: str,
) -> None:
    db.session.add(
        UnavailabilityEvent(
            unavailability=unavailability,
            event_type=event_type,
            previous_status=previous_status,
            new_status=new_status,
            description=description,
        )
    )
