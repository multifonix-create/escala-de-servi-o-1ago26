from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import func

from app.extensions import db
from app.models import (
    Assignment,
    AssignmentChange,
    AssignmentChangeType,
    AssignmentSource,
    FunctionalType,
    GenerationRun,
    GenerationRunStatus,
    Holiday,
    HolidayLeaveCredit,
    HolidayLeaveCreditEvent,
    HolidayLeaveCreditEventType,
    HolidayLeaveCreditStatus,
    HolidayScope,
    Military,
    ScheduleMonthStatus,
    ScheduleVersion,
    Unavailability,
    UnavailabilityStatus,
)
from app.services import cycle_calculator, membership_service
from app.services.schedule_version_policy import ScheduleVersionPolicy
from app.services.schedule_version_workflow import touch_version_content
from app.services.unavailability_evaluator import interval_for_unavailability, overlaps


FF_ELIGIBLE_SERVICE_CODES = ("AT1", "AT2", "AT3", "PO1", "PO2", "PO3", "PT", "R", "CR")
FF_SOURCE_VERSION_STATUSES = {
    ScheduleMonthStatus.VALIDATED.value,
    ScheduleMonthStatus.PUBLISHED.value,
    ScheduleMonthStatus.CLOSED.value,
}
FF_SCHEDULE_STATUSES = {
    HolidayLeaveCreditStatus.PENDING.value,
    HolidayLeaveCreditStatus.RESCHEDULED.value,
}


class HolidayCreditServiceError(Exception):
    def __init__(self, message: str, errors: dict[str, str] | None = None):
        super().__init__(message)
        self.errors = errors or {}


@dataclass(frozen=True)
class PotentialHolidayCredit:
    assignment: Assignment
    holiday: Holiday
    existing_credit: HolidayLeaveCredit | None = None

    @property
    def is_new(self) -> bool:
        return self.existing_credit is None


@dataclass(frozen=True)
class HolidayLeaveBalance:
    military: Military
    acquired: int
    pending: int
    scheduled: int
    used: int
    cancelled: int

    @property
    def available(self) -> int:
        return self.pending


def list_holidays(include_inactive: bool = False) -> list[Holiday]:
    query = Holiday.query
    if not include_inactive:
        query = query.filter_by(is_active=True)
    return query.order_by(Holiday.holiday_date.desc(), Holiday.scope.asc(), Holiday.name.asc()).all()


def create_holiday(payload: dict) -> Holiday:
    holiday = Holiday(
        holiday_date=_parse_date(payload.get("holiday_date")),
        name=_required_text(payload.get("name"), "name", "Indique o nome do feriado."),
        scope=_valid_scope(payload.get("scope")),
        notes=_optional_text(payload.get("notes")),
        is_active=True,
    )
    _ensure_unique_holiday(holiday.holiday_date, holiday.scope)
    db.session.add(holiday)
    db.session.commit()
    return holiday


def update_holiday(holiday: Holiday, payload: dict) -> Holiday:
    holiday_date = _parse_date(payload.get("holiday_date"))
    scope = _valid_scope(payload.get("scope"))
    if holiday.holiday_date != holiday_date or holiday.scope != scope:
        _ensure_unique_holiday(holiday_date, scope, exclude_id=holiday.id)
    holiday.holiday_date = holiday_date
    holiday.name = _required_text(payload.get("name"), "name", "Indique o nome do feriado.")
    holiday.scope = scope
    holiday.notes = _optional_text(payload.get("notes"))
    db.session.commit()
    return holiday


def set_holiday_active(holiday: Holiday, is_active: bool) -> Holiday:
    holiday.is_active = is_active
    db.session.commit()
    return holiday


def list_potential_credits(schedule_version: ScheduleVersion) -> list[PotentialHolidayCredit]:
    month_start, month_end = _version_bounds(schedule_version)
    holidays = (
        Holiday.query.filter(
            Holiday.is_active.is_(True),
            Holiday.holiday_date >= month_start,
            Holiday.holiday_date <= month_end,
        )
        .order_by(Holiday.holiday_date.asc(), Holiday.scope.asc())
        .all()
    )
    holidays_by_date = {item.holiday_date: item for item in holidays}
    if not holidays_by_date:
        return []
    assignments = (
        Assignment.query.filter(
            Assignment.schedule_version_id == schedule_version.id,
            Assignment.is_cleared.is_(False),
            Assignment.code.in_(FF_ELIGIBLE_SERVICE_CODES),
            Assignment.assignment_date.in_(list(holidays_by_date.keys())),
        )
        .order_by(Assignment.assignment_date.asc(), Assignment.code.asc(), Assignment.military_id.asc())
        .all()
    )
    credits = {
        credit.source_assignment_id: credit
        for credit in HolidayLeaveCredit.query.filter(
            HolidayLeaveCredit.source_assignment_id.in_([item.id for item in assignments])
        ).all()
    } if assignments else {}
    return [
        PotentialHolidayCredit(
            assignment=assignment,
            holiday=holidays_by_date[assignment.assignment_date],
            existing_credit=credits.get(assignment.id),
        )
        for assignment in assignments
    ]


def create_credit_from_assignment(
    assignment: Assignment,
    holiday: Holiday,
    manual_confirmation: bool = False,
    notes: str | None = None,
) -> HolidayLeaveCredit:
    _validate_credit_source(assignment, holiday, manual_confirmation)
    existing = HolidayLeaveCredit.query.filter_by(source_assignment_id=assignment.id).one_or_none()
    if existing is not None:
        return existing
    latest_run = _latest_generation_run_for_version(assignment.schedule_version_id)
    try:
        credit = HolidayLeaveCredit(
            military_id=assignment.military_id,
            holiday_id=holiday.id,
            source_assignment_id=assignment.id,
            source_schedule_version_id=assignment.schedule_version_id,
            source_generation_run_id=latest_run.id if latest_run else None,
            service_date=assignment.assignment_date,
            service_code=assignment.code,
            status=HolidayLeaveCreditStatus.PENDING.value,
            notes=_optional_text(notes),
        )
        db.session.add(credit)
        db.session.flush()
        _add_event(
            credit,
            HolidayLeaveCreditEventType.CREATED.value,
            None,
            credit.status,
            None,
            None,
            "Direito FF criado a partir de servico em feriado.",
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return credit


def schedule_credit(
    credit: HolidayLeaveCredit,
    schedule_version: ScheduleVersion,
    scheduled_date: date,
    notes: str | None = None,
    event_type: str = HolidayLeaveCreditEventType.SCHEDULED.value,
    allowed_statuses: set[str] | None = None,
) -> Assignment:
    previous_status = credit.status
    previous_scheduled_date = credit.scheduled_date
    _validate_schedule_target(credit, schedule_version, scheduled_date, allowed_statuses=allowed_statuses)
    try:
        assignment = Assignment.query.filter_by(
            schedule_version_id=schedule_version.id,
            military_id=credit.military_id,
            assignment_date=scheduled_date,
        ).one_or_none()
        if assignment is None:
            assignment = Assignment(
                schedule_version_id=schedule_version.id,
                military_id=credit.military_id,
                assignment_date=scheduled_date,
                code="FF",
                source=AssignmentSource.MANUAL.value,
                is_manual=True,
                is_locked=True,
                has_override=False,
                notes=_optional_text(notes),
                holiday_leave_credit_id=credit.id,
            )
            db.session.add(assignment)
            db.session.flush()
            _add_assignment_change(assignment, AssignmentChangeType.CREATED.value, None, "FF", None, True, None, False, notes)
        else:
            previous_code = assignment.code
            previous_locked = assignment.is_locked
            previous_override = assignment.has_override
            assignment.code = "FF"
            assignment.source = AssignmentSource.MANUAL.value
            assignment.is_manual = True
            assignment.is_locked = True
            assignment.has_override = False
            assignment.override_reason = None
            assignment.notes = _optional_text(notes)
            assignment.is_cleared = False
            assignment.holiday_leave_credit_id = credit.id
            _add_assignment_change(assignment, AssignmentChangeType.UPDATED.value, previous_code, "FF", previous_locked, True, previous_override, False, notes)

        credit.status = HolidayLeaveCreditStatus.RESCHEDULED.value if event_type == HolidayLeaveCreditEventType.RESCHEDULED.value else HolidayLeaveCreditStatus.SCHEDULED.value
        credit.scheduled_date = scheduled_date
        credit.effective_date = None
        touch_version_content(schedule_version)
        _add_event(
            credit,
            event_type,
            previous_status,
            credit.status,
            previous_scheduled_date,
            scheduled_date,
            "FF agendada na escala.",
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return assignment


def reschedule_credit(credit: HolidayLeaveCredit, schedule_version: ScheduleVersion, scheduled_date: date, notes: str | None = None) -> Assignment:
    if credit.status not in {HolidayLeaveCreditStatus.SCHEDULED.value, HolidayLeaveCreditStatus.RESCHEDULED.value}:
        raise HolidayCreditServiceError("Apenas FF agendada pode ser reagendada.", {"status": "A FF nao esta agendada."})
    _clear_linked_assignment(credit, "Reagendamento de FF.")
    db.session.flush()
    return schedule_credit(
        credit,
        schedule_version,
        scheduled_date,
        notes=notes,
        event_type=HolidayLeaveCreditEventType.RESCHEDULED.value,
        allowed_statuses={
            HolidayLeaveCreditStatus.SCHEDULED.value,
            HolidayLeaveCreditStatus.RESCHEDULED.value,
        },
    )


def cancel_schedule(credit: HolidayLeaveCredit, reason: str | None = None) -> HolidayLeaveCredit:
    if credit.status not in {HolidayLeaveCreditStatus.SCHEDULED.value, HolidayLeaveCreditStatus.RESCHEDULED.value}:
        raise HolidayCreditServiceError("Apenas FF agendada pode cancelar agendamento.", {"status": "A FF nao esta agendada."})
    previous_status = credit.status
    previous_date = credit.scheduled_date
    try:
        _clear_linked_assignment(credit, reason or "Cancelamento do agendamento de FF.")
        credit.status = HolidayLeaveCreditStatus.PENDING.value
        credit.scheduled_date = None
        credit.effective_date = None
        _add_event(
            credit,
            HolidayLeaveCreditEventType.SCHEDULE_CANCELLED.value,
            previous_status,
            credit.status,
            previous_date,
            None,
            reason or "Agendamento de FF cancelado.",
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return credit


def confirm_credit_used(credit: HolidayLeaveCredit, description: str | None = None) -> HolidayLeaveCredit:
    if credit.status not in {HolidayLeaveCreditStatus.SCHEDULED.value, HolidayLeaveCreditStatus.RESCHEDULED.value}:
        raise HolidayCreditServiceError("Apenas FF agendada pode ser confirmada como gozada.", {"status": "A FF nao esta agendada."})
    if credit.scheduled_date is None:
        raise HolidayCreditServiceError("FF agendada sem data.", {"scheduled_date": "A FF nao possui data agendada."})
    assignment = _linked_visible_ff_assignment(credit)
    if assignment is None:
        raise HolidayCreditServiceError("FF sem celula correspondente.", {"assignment": "Nao existe celula FF visivel ligada ao credito."})
    previous_status = credit.status
    try:
        credit.status = HolidayLeaveCreditStatus.USED.value
        credit.effective_date = credit.scheduled_date
        _add_event(
            credit,
            HolidayLeaveCreditEventType.USED.value,
            previous_status,
            credit.status,
            credit.scheduled_date,
            credit.scheduled_date,
            description or "Gozo de FF confirmado.",
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return credit


def cancel_credit_right(credit: HolidayLeaveCredit, reason: str | None) -> HolidayLeaveCredit:
    reason = _required_text(reason, "reason", "Indique o motivo do cancelamento do direito.")
    previous_status = credit.status
    previous_date = credit.scheduled_date
    try:
        if credit.status in {HolidayLeaveCreditStatus.SCHEDULED.value, HolidayLeaveCreditStatus.RESCHEDULED.value}:
            _clear_linked_assignment(credit, reason)
        credit.status = HolidayLeaveCreditStatus.CANCELLED.value
        credit.scheduled_date = None
        credit.effective_date = None
        credit.cancellation_reason = reason
        _add_event(
            credit,
            HolidayLeaveCreditEventType.CANCELLED.value,
            previous_status,
            credit.status,
            previous_date,
            None,
            reason,
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return credit


def list_credits(status: str | None = None, military_id: int | None = None) -> list[HolidayLeaveCredit]:
    query = HolidayLeaveCredit.query
    if status:
        query = query.filter_by(status=status)
    if military_id:
        query = query.filter_by(military_id=military_id)
    return query.order_by(HolidayLeaveCredit.service_date.desc(), HolidayLeaveCredit.id.desc()).all()


def balance_by_military() -> list[HolidayLeaveBalance]:
    militaries = Military.query.order_by(Military.name.asc(), Military.nim.asc()).all()
    rows = []
    counts = (
        db.session.query(
            HolidayLeaveCredit.military_id,
            HolidayLeaveCredit.status,
            func.count(HolidayLeaveCredit.id),
        )
        .group_by(HolidayLeaveCredit.military_id, HolidayLeaveCredit.status)
        .all()
    )
    by_military: dict[int, dict[str, int]] = {}
    for military_id, status, count in counts:
        by_military.setdefault(military_id, {})[status] = count
    for military in militaries:
        statuses = by_military.get(military.id, {})
        pending = statuses.get(HolidayLeaveCreditStatus.PENDING.value, 0) + statuses.get(HolidayLeaveCreditStatus.RESCHEDULED.value, 0)
        rows.append(
            HolidayLeaveBalance(
                military=military,
                acquired=sum(statuses.values()),
                pending=pending,
                scheduled=statuses.get(HolidayLeaveCreditStatus.SCHEDULED.value, 0),
                used=statuses.get(HolidayLeaveCreditStatus.USED.value, 0),
                cancelled=statuses.get(HolidayLeaveCreditStatus.CANCELLED.value, 0),
            )
        )
    return rows


def _validate_credit_source(assignment: Assignment, holiday: Holiday, manual_confirmation: bool) -> None:
    if assignment is None or not assignment.is_visible:
        raise HolidayCreditServiceError("Atribuicao invalida.", {"assignment": "A atribuicao de origem nao existe ou esta limpa."})
    if assignment.code not in FF_ELIGIBLE_SERVICE_CODES:
        raise HolidayCreditServiceError("Codigo sem direito FF nesta fase.", {"code": "O codigo nao e elegivel para FF."})
    if holiday is None or not holiday.is_active:
        raise HolidayCreditServiceError("Feriado invalido.", {"holiday": "O feriado deve estar ativo."})
    if assignment.assignment_date != holiday.holiday_date:
        raise HolidayCreditServiceError("Data incoerente.", {"holiday": "O feriado nao corresponde a data do servico."})
    if assignment.military.functional_type == FunctionalType.CMD.value and assignment.code not in {"R", "CR"}:
        raise HolidayCreditServiceError("CMD nao e elegivel para FF operacional.", {"military": "CMD nao executa servico operacional elegivel."})
    if assignment.schedule_version.status not in FF_SOURCE_VERSION_STATUSES and not manual_confirmation:
        raise HolidayCreditServiceError(
            "Confirmacao necessaria.",
            {"confirmation": "Confirme explicitamente que o servico em feriado foi prestado."},
        )


def _validate_schedule_target(
    credit: HolidayLeaveCredit,
    schedule_version: ScheduleVersion,
    scheduled_date: date,
    allowed_statuses: set[str] | None = None,
) -> None:
    if credit.status not in (allowed_statuses or FF_SCHEDULE_STATUSES):
        raise HolidayCreditServiceError("Estado da FF nao permite agendamento.", {"status": "A FF nao esta pendente."})
    if not ScheduleVersionPolicy(schedule_version).can_schedule_ff():
        raise HolidayCreditServiceError("Versao nao editavel.", {"status": "A FF so pode ser agendada em versao DRAFT."})
    if not _date_belongs_to_version(schedule_version, scheduled_date):
        raise HolidayCreditServiceError("Data fora do mes.", {"scheduled_date": "A data nao pertence ao mes da versao."})
    if not _military_in_period(credit.military, scheduled_date):
        raise HolidayCreditServiceError("Militar fora do periodo.", {"military": "O militar esta fora do periodo de efetividade."})
    existing = Assignment.query.filter_by(
        schedule_version_id=schedule_version.id,
        military_id=credit.military_id,
        assignment_date=scheduled_date,
    ).one_or_none()
    if existing is not None and existing.is_visible and existing.holiday_leave_credit_id != credit.id:
        raise HolidayCreditServiceError("Celula ocupada.", {"assignment": "A data ja possui atribuicao visivel para este militar."})
    if existing is not None and existing.is_visible and existing.code == "FF" and existing.holiday_leave_credit_id == credit.id:
        raise HolidayCreditServiceError("FF ja agendada nesta data.", {"assignment": "A FF ja esta ligada a esta celula."})
    if _has_unavailability(credit.military_id, scheduled_date):
        raise HolidayCreditServiceError("Indisponibilidade na data.", {"unavailability": "A data possui indisponibilidade ativa e fica bloqueada nesta versao."})
    if _cycle_code_for_military(credit.military, scheduled_date) in {"DS", "DC"}:
        raise HolidayCreditServiceError("Data coincide com DS/DC.", {"cycle": "A FF nao deve ser agendada em DS/DC nesta versao."})


def _clear_linked_assignment(credit: HolidayLeaveCredit, reason: str) -> None:
    touched_versions = set()
    for assignment in _linked_visible_ff_assignments(credit):
        previous_code = assignment.code
        previous_override = assignment.has_override
        assignment.code = None
        assignment.has_override = False
        assignment.override_reason = None
        assignment.is_cleared = True
        assignment.holiday_leave_credit_id = None
        _add_assignment_change(
            assignment,
            AssignmentChangeType.CLEARED.value,
            previous_code,
            None,
            assignment.is_locked,
            assignment.is_locked,
            previous_override,
            False,
            reason,
        )
        if assignment.schedule_version_id not in touched_versions:
            touch_version_content(assignment.schedule_version)
            touched_versions.add(assignment.schedule_version_id)


def _linked_visible_ff_assignment(credit: HolidayLeaveCredit) -> Assignment | None:
    assignments = _linked_visible_ff_assignments(credit)
    return assignments[0] if assignments else None


def _linked_visible_ff_assignments(credit: HolidayLeaveCredit) -> list[Assignment]:
    if credit.scheduled_date is None:
        return []
    return Assignment.query.filter_by(
        holiday_leave_credit_id=credit.id,
        military_id=credit.military_id,
        assignment_date=credit.scheduled_date,
        code="FF",
        is_cleared=False,
    ).join(ScheduleVersion, Assignment.schedule_version_id == ScheduleVersion.id).filter(
        ScheduleVersion.status == ScheduleMonthStatus.DRAFT.value
    ).order_by(Assignment.schedule_version_id.desc(), Assignment.id.desc()).all()


def _has_unavailability(military_id: int, scheduled_date: date) -> bool:
    day_start = datetime.combine(scheduled_date, time.min)
    day_end = day_start + timedelta(days=1)
    candidates = Unavailability.query.filter(
        Unavailability.military_id == military_id,
        Unavailability.is_active.is_(True),
        Unavailability.status != UnavailabilityStatus.CANCELLED.value,
        Unavailability.start_date <= scheduled_date,
        Unavailability.end_date >= scheduled_date - timedelta(days=1),
    ).all()
    for unavailability in candidates:
        interval = interval_for_unavailability(unavailability)
        if overlaps(interval.effective_start, interval.effective_end, day_start, day_end):
            return True
    return False


def _cycle_code_for_military(military: Military, scheduled_date: date) -> str | None:
    if military.functional_type != FunctionalType.PATRULHEIRO.value:
        return None
    team = membership_service.get_team_for_military_on_date(military.id, scheduled_date)
    if team is None:
        return None
    try:
        return cycle_calculator.calculate_team_day(team, scheduled_date).code
    except cycle_calculator.MissingTeamReferenceError:
        return None


def _date_belongs_to_version(schedule_version: ScheduleVersion, candidate_date: date) -> bool:
    month = schedule_version.schedule_month
    last_day = monthrange(month.year, month.month)[1]
    return date(month.year, month.month, 1) <= candidate_date <= date(month.year, month.month, last_day)


def _version_bounds(schedule_version: ScheduleVersion) -> tuple[date, date]:
    month = schedule_version.schedule_month
    return date(month.year, month.month, 1), date(month.year, month.month, monthrange(month.year, month.month)[1])


def _military_in_period(military: Military, scheduled_date: date) -> bool:
    return military.start_date <= scheduled_date and (
        military.end_date is None or scheduled_date <= military.end_date
    )


def _latest_generation_run_for_version(schedule_version_id: int) -> GenerationRun | None:
    return (
        GenerationRun.query.filter(
            GenerationRun.schedule_version_id == schedule_version_id,
            GenerationRun.status.in_(
                [
                    GenerationRunStatus.COMPLETED.value,
                    GenerationRunStatus.COMPLETED_WITH_WARNINGS.value,
                ]
            ),
        )
        .order_by(GenerationRun.created_at.desc(), GenerationRun.id.desc())
        .first()
    )


def _add_event(
    credit: HolidayLeaveCredit,
    event_type: str,
    previous_status: str | None,
    new_status: str | None,
    previous_scheduled_date: date | None,
    new_scheduled_date: date | None,
    description: str | None,
) -> None:
    db.session.add(
        HolidayLeaveCreditEvent(
            credit=credit,
            event_type=event_type,
            previous_status=previous_status,
            new_status=new_status,
            previous_scheduled_date=previous_scheduled_date,
            new_scheduled_date=new_scheduled_date,
            description=description,
        )
    )


def _add_assignment_change(
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


def _ensure_unique_holiday(holiday_date: date, scope: str, exclude_id: int | None = None) -> None:
    query = Holiday.query.filter_by(holiday_date=holiday_date, scope=scope)
    if exclude_id is not None:
        query = query.filter(Holiday.id != exclude_id)
    if query.first() is not None:
        raise HolidayCreditServiceError("Feriado duplicado.", {"holiday_date": "Ja existe feriado com esta data e ambito."})


def _parse_date(value: str | date | None) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat((value or "").strip())
    except ValueError as exc:
        raise HolidayCreditServiceError("Data invalida.", {"holiday_date": "Indique uma data valida."}) from exc


def _valid_scope(value: str | None) -> str:
    normalized = (value or "").strip().upper()
    if normalized not in {item.value for item in HolidayScope}:
        raise HolidayCreditServiceError("Ambito invalido.", {"scope": "Indique um ambito de feriado valido."})
    return normalized


def _required_text(value: str | None, key: str, message: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise HolidayCreditServiceError(message, {key: message})
    return normalized


def _optional_text(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None
