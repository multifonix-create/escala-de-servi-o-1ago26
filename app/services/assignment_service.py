from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from app.extensions import db
from app.models import (
    Assignment,
    AssignmentChange,
    AssignmentChangeType,
    AssignmentSource,
    FunctionalType,
    Military,
    ScheduleMonthStatus,
    ScheduleVersion,
    Unavailability,
    UnavailabilityStatus,
)
from app.services import cycle_calculator, membership_service, restriction_service
from app.services.assignment_codes import (
    ALLOWED_ASSIGNMENT_CODES,
    OPERATIONAL_ASSIGNMENT_CODES,
    UNAVAILABILITY_ASSIGNMENT_CODES,
)
from app.services.unavailability_evaluator import interval_for_unavailability, overlaps
from app.services.schedule_version_policy import ScheduleVersionPolicy
from app.services.schedule_version_workflow import touch_version_content


EDITABLE_VERSION_STATUSES = {ScheduleMonthStatus.DRAFT.value}


class AssignmentServiceError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__("Dados de atribuicao invalidos.")
        self.errors = errors


@dataclass(frozen=True)
class AssignmentValidationResult:
    is_valid: bool
    blocking_errors: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    requires_override: bool = False
    cycle_code: str | None = None
    unavailability: Unavailability | None = None
    restrictions: list = field(default_factory=list)
    explanation: str = ""


def get_assignment(
    schedule_version_id: int,
    military_id: int,
    assignment_date: date,
) -> Assignment | None:
    return Assignment.query.filter_by(
        schedule_version_id=schedule_version_id,
        military_id=military_id,
        assignment_date=assignment_date,
    ).one_or_none()


def list_changes(assignment: Assignment) -> list[AssignmentChange]:
    return (
        AssignmentChange.query.filter_by(assignment_id=assignment.id)
        .order_by(AssignmentChange.created_at.asc(), AssignmentChange.id.asc())
        .all()
    )


def validate_assignment(
    schedule_version: ScheduleVersion | None,
    military: Military | None,
    assignment_date: date,
    code: str,
    override_requested: bool = False,
    override_reason: str | None = None,
) -> AssignmentValidationResult:
    blocking_errors: dict[str, str] = {}
    warnings: list[str] = []
    cycle_code = None
    selected_unavailability = None
    restrictions = []
    normalized_code = normalize_code(code)

    if schedule_version is None:
        blocking_errors["schedule_version"] = "Versao inexistente."
    elif not ScheduleVersionPolicy(schedule_version).can_edit():
        blocking_errors["status"] = "A versao selecionada nao permite edicao."
    elif not _date_belongs_to_version(schedule_version, assignment_date):
        blocking_errors["assignment_date"] = "A data nao pertence ao mes da versao."

    if military is None:
        blocking_errors["military"] = "Militar inexistente."
    elif not _military_in_period(military, assignment_date):
        blocking_errors["military_period"] = "O militar esta fora do periodo de efetividade nesta data."

    if normalized_code not in ALLOWED_ASSIGNMENT_CODES:
        blocking_errors["code"] = "Codigo nao permitido."

    if blocking_errors:
        return AssignmentValidationResult(
            is_valid=False,
            blocking_errors=blocking_errors,
            warnings=warnings,
            requires_override=False,
            explanation="Existem erros bloqueantes.",
        )

    if military.functional_type == FunctionalType.PATRULHEIRO.value:
        team = membership_service.get_team_for_military_on_date(military.id, assignment_date)
        if team is None:
            warnings.append("Militar sem equipa valida nesta data.")
        else:
            try:
                cycle_day = cycle_calculator.calculate_team_day(team, assignment_date)
            except cycle_calculator.MissingTeamReferenceError:
                warnings.append("Equipa sem referencia de ciclo valida nesta data.")
            else:
                cycle_code = cycle_day.code
                if cycle_code in {"DS", "DC"} and normalized_code not in {cycle_code}:
                    warnings.append(f"Atribuicao manual em dia de {cycle_code}.")
                if normalized_code in {"DS", "DC"} and normalized_code != cycle_code:
                    warnings.append("Codigo DS/DC manual diferente do ciclo calculado.")

    unavailabilities = _unavailabilities_for_day(military.id, assignment_date)
    selected_unavailability = unavailabilities[0] if unavailabilities else None
    for unavailability in unavailabilities:
        if unavailability.status == UnavailabilityStatus.CONFIRMED.value:
            if unavailability.code == "BM":
                blocking_errors["unavailability"] = "BM confirmada bloqueia a atribuicao sem excecao funcional documentada."
            elif normalized_code not in UNAVAILABILITY_ASSIGNMENT_CODES:
                warnings.append(f"Indisponibilidade confirmada {unavailability.code} exige override explicito.")
        elif unavailability.status == UnavailabilityStatus.PLANNED.value:
            warnings.append(f"Indisponibilidade planeada {unavailability.code} nesta data.")

    if normalized_code in UNAVAILABILITY_ASSIGNMENT_CODES and not any(
        item.code == normalized_code for item in unavailabilities
    ):
        warnings.append("Codigo de indisponibilidade sem indisponibilidade registada correspondente.")

    restrictions = [
        restriction
        for restriction in restriction_service.get_active_restrictions_for_military_on_date(military.id, assignment_date)
        if restriction.applies_to_weekday(assignment_date.weekday())
    ]
    if restrictions and normalized_code in OPERATIONAL_ASSIGNMENT_CODES:
        warnings.append("Existem restricoes individuais aplicaveis nesta data.")

    if normalized_code in {"FF", "FC", "FR"}:
        blocking_errors["compensation"] = "FF, FC e FR devem ser geridas pelos modulos proprios."
    if normalized_code in {"R", "CR"}:
        warnings.append("R/CR ainda nao possui validacao operacional completa.")

    requires_override = bool(warnings)
    if requires_override and not override_requested:
        blocking_errors["override"] = "A atribuicao exige override explicito."
    if override_requested and requires_override and not (override_reason or "").strip():
        blocking_errors["override_reason"] = "O motivo do override e obrigatorio."

    return AssignmentValidationResult(
        is_valid=not blocking_errors,
        blocking_errors=blocking_errors,
        warnings=warnings,
        requires_override=requires_override,
        cycle_code=cycle_code,
        unavailability=selected_unavailability,
        restrictions=restrictions,
        explanation="; ".join(warnings) if warnings else "Atribuicao sem conflitos detetados.",
    )


def save_manual_assignment(
    schedule_version: ScheduleVersion,
    military: Military,
    assignment_date: date,
    code: str,
    notes: str | None = None,
    override_requested: bool = False,
    override_reason: str | None = None,
    lock_assignment: bool = True,
) -> tuple[Assignment, AssignmentValidationResult]:
    normalized_code = normalize_code(code)
    assignment = get_assignment(schedule_version.id, military.id, assignment_date)
    if assignment and assignment.is_visible:
        _ensure_not_linked_leave_cell(assignment)
    if assignment and assignment.is_locked and not assignment.is_cleared:
        raise AssignmentServiceError({"locked": "A celula esta bloqueada. Desbloqueie antes de alterar."})

    validation = validate_assignment(
        schedule_version,
        military,
        assignment_date,
        normalized_code,
        override_requested=override_requested,
        override_reason=override_reason,
    )
    if not validation.is_valid:
        raise AssignmentServiceError(validation.blocking_errors)

    try:
        if assignment is None:
            assignment = Assignment(
                schedule_version_id=schedule_version.id,
                military_id=military.id,
                assignment_date=assignment_date,
                code=normalized_code,
                source=AssignmentSource.MANUAL.value,
                is_manual=True,
                is_locked=lock_assignment,
                has_override=validation.requires_override,
                override_reason=override_reason if validation.requires_override else None,
                notes=notes,
                is_cleared=False,
            )
            db.session.add(assignment)
            db.session.flush()
            _add_change(assignment, AssignmentChangeType.CREATED.value, None, assignment.code, None, assignment.is_locked, None, assignment.has_override, override_reason or notes)
            if assignment.has_override:
                _add_change(assignment, AssignmentChangeType.OVERRIDE_APPLIED.value, assignment.code, assignment.code, assignment.is_locked, assignment.is_locked, False, True, override_reason)
        else:
            previous_code = assignment.code
            previous_locked = assignment.is_locked
            previous_override = assignment.has_override
            assignment.code = normalized_code
            assignment.source = AssignmentSource.MANUAL.value
            assignment.is_manual = True
            assignment.is_locked = lock_assignment
            assignment.has_override = validation.requires_override
            assignment.override_reason = override_reason if validation.requires_override else None
            assignment.notes = notes
            assignment.is_cleared = False
            _add_change(assignment, AssignmentChangeType.UPDATED.value, previous_code, assignment.code, previous_locked, assignment.is_locked, previous_override, assignment.has_override, override_reason or notes)
            if not previous_override and assignment.has_override:
                _add_change(assignment, AssignmentChangeType.OVERRIDE_APPLIED.value, previous_code, assignment.code, previous_locked, assignment.is_locked, False, True, override_reason)
            if previous_override and not assignment.has_override:
                _add_change(assignment, AssignmentChangeType.OVERRIDE_REMOVED.value, previous_code, assignment.code, previous_locked, assignment.is_locked, True, False, "Conflito removido pela nova atribuicao.")
        touch_version_content(schedule_version)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return assignment, validation


def clear_assignment(assignment: Assignment, reason: str | None = None) -> Assignment:
    if not ScheduleVersionPolicy(assignment.schedule_version).can_edit():
        raise AssignmentServiceError({"status": "A versao selecionada nao permite edicao."})
    _ensure_not_linked_leave_cell(assignment)
    if assignment.is_locked:
        raise AssignmentServiceError({"locked": "A celula esta bloqueada. Desbloqueie antes de limpar."})
    previous_code = assignment.code
    previous_override = assignment.has_override
    try:
        assignment.code = None
        assignment.has_override = False
        assignment.override_reason = None
        assignment.is_cleared = True
        _add_change(assignment, AssignmentChangeType.CLEARED.value, previous_code, None, assignment.is_locked, assignment.is_locked, previous_override, False, reason)
        touch_version_content(assignment.schedule_version)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return assignment


def lock_assignment(assignment: Assignment, reason: str | None = None) -> Assignment:
    if not ScheduleVersionPolicy(assignment.schedule_version).can_edit():
        raise AssignmentServiceError({"status": "A versao selecionada nao permite edicao."})
    if assignment.is_locked:
        return assignment
    try:
        assignment.is_locked = True
        _add_change(assignment, AssignmentChangeType.LOCKED.value, assignment.code, assignment.code, False, True, assignment.has_override, assignment.has_override, reason)
        touch_version_content(assignment.schedule_version)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return assignment


def unlock_assignment(assignment: Assignment, reason: str | None = None) -> Assignment:
    if not ScheduleVersionPolicy(assignment.schedule_version).can_edit():
        raise AssignmentServiceError({"status": "A versao selecionada nao permite edicao."})
    _ensure_not_linked_leave_cell(assignment)
    if not assignment.is_locked:
        return assignment
    try:
        assignment.is_locked = False
        _add_change(assignment, AssignmentChangeType.UNLOCKED.value, assignment.code, assignment.code, True, False, assignment.has_override, assignment.has_override, reason)
        touch_version_content(assignment.schedule_version)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return assignment


def normalize_code(code: str) -> str:
    return (code or "").strip().upper()


def _date_belongs_to_version(schedule_version: ScheduleVersion, assignment_date: date) -> bool:
    schedule_month = schedule_version.schedule_month
    last_day = monthrange(schedule_month.year, schedule_month.month)[1]
    return date(schedule_month.year, schedule_month.month, 1) <= assignment_date <= date(
        schedule_month.year,
        schedule_month.month,
        last_day,
    )


def _military_in_period(military: Military, assignment_date: date) -> bool:
    return military.start_date <= assignment_date and (
        military.end_date is None or assignment_date <= military.end_date
    )


def _unavailabilities_for_day(military_id: int, assignment_date: date) -> list[Unavailability]:
    day_start = datetime.combine(assignment_date, time.min)
    day_end = day_start + timedelta(days=1)
    matches = []
    candidates = (
        Unavailability.query.filter(
            Unavailability.military_id == military_id,
            Unavailability.is_active.is_(True),
            Unavailability.status != UnavailabilityStatus.CANCELLED.value,
            Unavailability.start_date <= assignment_date,
            Unavailability.end_date >= assignment_date - timedelta(days=1),
        )
        .order_by(Unavailability.status.asc(), Unavailability.start_date.asc(), Unavailability.id.asc())
        .all()
    )
    for unavailability in candidates:
        interval = interval_for_unavailability(unavailability)
        if overlaps(interval.effective_start, interval.effective_end, day_start, day_end):
            matches.append(unavailability)
    matches.sort(key=lambda item: (0 if item.status == UnavailabilityStatus.CONFIRMED.value else 1, item.start_date, item.id))
    return matches


def _add_change(
    assignment: Assignment,
    change_type: str,
    previous_code: str | None,
    new_code: str | None,
    previous_locked: bool | None,
    new_locked: bool | None,
    previous_override: bool | None,
    new_override: bool | None,
    reason: str | None,
) -> None:
    db.session.add(
        AssignmentChange(
            assignment=assignment,
            change_type=change_type,
            previous_code=previous_code,
            new_code=new_code,
            previous_locked=previous_locked,
            new_locked=new_locked,
            previous_override=previous_override,
            new_override=new_override,
            reason=reason,
        )
    )


def _ensure_not_linked_leave_cell(assignment: Assignment) -> None:
    if assignment.holiday_leave_credit_id is not None:
        raise AssignmentServiceError(
            {"holiday_leave_credit": "A celula esta ligada a uma FF. Use as opcoes de FF para cancelar ou reagendar."}
        )
    if assignment.compensatory_leave_credit_id is not None:
        raise AssignmentServiceError(
            {"compensatory_leave_credit": "A celula esta ligada a uma FC. Use as opcoes de FC para cancelar ou reagendar."}
        )
    if assignment.rescheduled_rest_credit_id is not None:
        raise AssignmentServiceError(
            {"rescheduled_rest_credit": "A celula esta ligada a uma FR. Use as opcoes de folgas reagendadas para cancelar ou reagendar."}
        )
