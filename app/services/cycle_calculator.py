from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import or_

from app.extensions import db
from app.models import Team, TeamCycleReference


VALID_PHASES = tuple(range(1, 7))
MAX_PREVIEW_DAYS = 120

PHASE_DAYS_OFF = {
    1: {5: "DS", 6: "DC"},
    2: {4: "DS"},
    3: {3: "DS", 4: "DC"},
    4: {2: "DS", 3: "DC"},
    5: {1: "DS", 2: "DC"},
    6: {0: "DS"},
}

WEEKDAY_NAMES = (
    "segunda-feira",
    "terça-feira",
    "quarta-feira",
    "quinta-feira",
    "sexta-feira",
    "sábado",
    "domingo",
)


class CycleCalculationError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__("Dados de ciclo inválidos.")
        self.errors = errors


class MissingTeamReferenceError(CycleCalculationError):
    pass


@dataclass(frozen=True)
class CycleExplanation:
    reference_id: int
    reference_date: date
    reference_week_monday: date
    target_date: date
    target_week_monday: date
    week_offset: int
    reference_phase: int
    calculated_phase: int
    day_code: str | None


@dataclass(frozen=True)
class CycleDay:
    day: date
    weekday_name: str
    phase: int
    code: str | None
    explanation: CycleExplanation


def monday_of_week(value: date) -> date:
    return value - timedelta(days=value.weekday())


def week_offset(reference_date: date, target_date: date) -> int:
    reference_monday = monday_of_week(reference_date)
    target_monday = monday_of_week(target_date)
    return (target_monday - reference_monday).days // 7


def calculate_phase(reference_phase: int, reference_date: date, target_date: date) -> int:
    validate_phase(reference_phase)
    offset = week_offset(reference_date, target_date)
    return ((reference_phase - 1 + offset) % 6) + 1


def day_off_code_for_phase(phase: int, target_date: date) -> str | None:
    validate_phase(phase)
    return PHASE_DAYS_OFF[phase].get(target_date.weekday())


def get_reference_for_team_on_date(
    team_id: int,
    target_date: date,
) -> TeamCycleReference | None:
    return (
        TeamCycleReference.query.filter(
            TeamCycleReference.team_id == team_id,
            TeamCycleReference.valid_from <= target_date,
            or_(
                TeamCycleReference.valid_until.is_(None),
                TeamCycleReference.valid_until >= target_date,
            ),
        )
        .order_by(TeamCycleReference.valid_from.desc())
        .one_or_none()
    )


def get_current_reference(team_id: int, today: date | None = None) -> TeamCycleReference | None:
    return get_reference_for_team_on_date(team_id, today or date.today())


def calculate_team_day(team: Team, target_date: date) -> CycleDay:
    reference = get_reference_for_team_on_date(team.id, target_date)
    if reference is None:
        raise MissingTeamReferenceError(
            {"reference": "A equipa não possui referência válida para a data indicada."}
        )

    phase = calculate_phase(
        reference.reference_phase,
        reference.reference_date,
        target_date,
    )
    code = day_off_code_for_phase(phase, target_date)
    explanation = explain_calculation(reference, target_date, phase, code)
    return CycleDay(
        day=target_date,
        weekday_name=WEEKDAY_NAMES[target_date.weekday()],
        phase=phase,
        code=code,
        explanation=explanation,
    )


def explain_calculation(
    reference: TeamCycleReference,
    target_date: date,
    calculated_phase: int | None = None,
    day_code: str | None = None,
) -> CycleExplanation:
    phase = calculated_phase or calculate_phase(
        reference.reference_phase,
        reference.reference_date,
        target_date,
    )
    code = day_code if day_code is not None else day_off_code_for_phase(phase, target_date)
    return CycleExplanation(
        reference_id=reference.id,
        reference_date=reference.reference_date,
        reference_week_monday=monday_of_week(reference.reference_date),
        target_date=target_date,
        target_week_monday=monday_of_week(target_date),
        week_offset=week_offset(reference.reference_date, target_date),
        reference_phase=reference.reference_phase,
        calculated_phase=phase,
        day_code=code,
    )


def preview_team_cycle(team: Team, start_date: date, end_date: date) -> list[CycleDay]:
    validate_preview_interval(start_date, end_date)
    days = []
    current = start_date
    while current <= end_date:
        days.append(calculate_team_day(team, current))
        current += timedelta(days=1)
    return days


def create_team_cycle_reference(
    team: Team | None,
    reference_date: date,
    reference_phase: int,
    valid_from: date,
    notes: str | None = None,
) -> TeamCycleReference:
    validate_team(team)
    validate_phase(reference_phase)

    current = get_reference_for_team_on_date(team.id, valid_from)
    if current and current.valid_from >= valid_from:
        raise CycleCalculationError(
            {"valid_from": "Já existe uma referência válida nesta data."}
        )

    if has_overlapping_reference(team.id, valid_from, None, excluded_id=current.id if current else None):
        raise CycleCalculationError(
            {"valid_from": "O período indicado sobrepõe-se a outra referência."}
        )

    reference = TeamCycleReference(
        team_id=team.id,
        reference_date=reference_date,
        reference_phase=reference_phase,
        valid_from=valid_from,
        notes=notes,
    )
    try:
        if current:
            current.valid_until = valid_from - timedelta(days=1)
        db.session.add(reference)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return reference


def list_references_for_team(team_id: int) -> list[TeamCycleReference]:
    return (
        TeamCycleReference.query.filter(TeamCycleReference.team_id == team_id)
        .order_by(TeamCycleReference.valid_from.desc(), TeamCycleReference.id.desc())
        .all()
    )


def has_overlapping_reference(
    team_id: int,
    valid_from: date,
    valid_until: date | None,
    excluded_id: int | None = None,
) -> bool:
    search_until = valid_until or date.max
    statement = TeamCycleReference.query.filter(
        TeamCycleReference.team_id == team_id,
        TeamCycleReference.valid_from <= search_until,
        or_(
            TeamCycleReference.valid_until.is_(None),
            TeamCycleReference.valid_until >= valid_from,
        ),
    )
    if excluded_id is not None:
        statement = statement.filter(TeamCycleReference.id != excluded_id)
    return db.session.query(statement.exists()).scalar()


def validate_phase(value: int) -> None:
    if value not in VALID_PHASES:
        raise CycleCalculationError({"reference_phase": "A fase deve estar entre 1 e 6."})


def validate_team(team: Team | None) -> None:
    if team is None or not team.is_active:
        raise CycleCalculationError({"team": "Selecione uma equipa ativa válida."})


def validate_preview_interval(start_date: date, end_date: date) -> None:
    if end_date < start_date:
        raise CycleCalculationError(
            {"end_date": "A data final não pode ser anterior à data inicial."}
        )
    if (end_date - start_date).days + 1 > MAX_PREVIEW_DAYS:
        raise CycleCalculationError(
            {"end_date": f"O intervalo não pode exceder {MAX_PREVIEW_DAYS} dias."}
        )
