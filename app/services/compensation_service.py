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
    CompensatoryLeaveCredit,
    CompensatoryLeaveCreditEvent,
    CompensatoryLeaveCreditEventType,
    CompensatoryLeaveCreditStatus,
    CompensatoryLeaveSourceType,
    FunctionalType,
    Holiday,
    Military,
    RescheduledRestCredit,
    RescheduledRestCreditEvent,
    RescheduledRestCreditEventType,
    RescheduledRestCreditStatus,
    ScheduleMonth,
    ScheduleMonthStatus,
    ScheduleVersion,
    Unavailability,
    UnavailabilityStatus,
)
from app.models.military import utc_now
from app.services import cycle_calculator, membership_service
from app.services.schedule_version_policy import ScheduleVersionPolicy
from app.services.schedule_version_workflow import touch_version_content
from app.services.unavailability_evaluator import interval_for_unavailability, overlaps


FC_SOURCE_CODES = {"R": CompensatoryLeaveSourceType.RONDA.value, "CR": CompensatoryLeaveSourceType.CONDUTOR_RONDANTE.value}
FR_SOURCE_CODES = {"AT1", "AT2", "AT3", "PO1", "PO2", "PO3", "PT"}
AVAILABLE_FC_STATUSES = {CompensatoryLeaveCreditStatus.PENDING.value, CompensatoryLeaveCreditStatus.RESCHEDULED.value}
AVAILABLE_FR_STATUSES = {RescheduledRestCreditStatus.PENDING.value, RescheduledRestCreditStatus.RESCHEDULED.value}


class CompensationServiceError(Exception):
    def __init__(self, message: str, errors: dict[str, str] | None = None):
        super().__init__(message)
        self.errors = errors or {}


@dataclass(frozen=True)
class PotentialCompensatoryLeave:
    assignment: Assignment
    source_type: str
    units: int
    existing_credits: list[CompensatoryLeaveCredit]
    is_holiday: bool = False

    @property
    def pending_units(self) -> int:
        return max(self.units - len(self.existing_credits), 0)

    @property
    def is_new(self) -> bool:
        return self.pending_units > 0 and not self.is_holiday


@dataclass(frozen=True)
class PotentialRescheduledRest:
    assignment: Assignment
    original_rest_type: str
    existing_credit: RescheduledRestCredit | None

    @property
    def is_new(self) -> bool:
        return self.existing_credit is None


@dataclass(frozen=True)
class CompensatoryLeaveBalance:
    military: Military
    acquired: int
    pending: int
    scheduled: int
    rescheduled: int
    used: int
    cancelled: int
    expired: int

    @property
    def available(self) -> int:
        return self.pending + self.rescheduled


@dataclass(frozen=True)
class RescheduledRestBalance:
    military: Military
    acquired: int
    pending: int
    scheduled: int
    rescheduled: int
    used: int
    cancelled: int

    @property
    def available(self) -> int:
        return self.pending + self.rescheduled


def list_fc_credits(status: str | None = None, military_id: int | None = None) -> list[CompensatoryLeaveCredit]:
    CompensationMaintenanceService().process()
    query = CompensatoryLeaveCredit.query
    if status:
        query = query.filter_by(status=status)
    if military_id:
        query = query.filter_by(military_id=military_id)
    return query.order_by(CompensatoryLeaveCredit.acquired_date.desc(), CompensatoryLeaveCredit.id.desc()).all()


def list_fr_credits(status: str | None = None, military_id: int | None = None) -> list[RescheduledRestCredit]:
    query = RescheduledRestCredit.query
    if status:
        query = query.filter_by(status=status)
    if military_id:
        query = query.filter_by(military_id=military_id)
    return query.order_by(RescheduledRestCredit.original_rest_date.desc(), RescheduledRestCredit.id.desc()).all()


def list_compensation_potentials(schedule_version: ScheduleVersion) -> tuple[list[PotentialCompensatoryLeave], list[PotentialRescheduledRest]]:
    assignments = (
        Assignment.query.filter(
            Assignment.schedule_version_id == schedule_version.id,
            Assignment.is_cleared.is_(False),
            Assignment.code.in_(tuple(set(FC_SOURCE_CODES) | FR_SOURCE_CODES)),
        )
        .order_by(Assignment.assignment_date.asc(), Assignment.code.asc(), Assignment.military_id.asc())
        .all()
    )
    holidays = {
        item.holiday_date
        for item in Holiday.query.filter(
            Holiday.is_active.is_(True),
            Holiday.holiday_date >= _version_start(schedule_version),
            Holiday.holiday_date <= _version_end(schedule_version),
        ).all()
    }
    fc_potentials = [_fc_potential_for_assignment(item, holidays) for item in assignments if item.code in FC_SOURCE_CODES]
    fr_potentials = [_fr_potential_for_assignment(item) for item in assignments if item.code in FR_SOURCE_CODES]
    return [item for item in fc_potentials if item is not None], [item for item in fr_potentials if item is not None]


def confirm_fc_from_assignment(assignment: Assignment, notes: str | None = None) -> list[CompensatoryLeaveCredit]:
    if assignment.code not in FC_SOURCE_CODES:
        raise CompensationServiceError("Codigo sem direito FC.", {"code": "Apenas R e CR originam FC nesta versao."})
    if _is_active_holiday(assignment.assignment_date):
        raise CompensationServiceError("R/CR em feriado nao gera FC.", {"holiday": "Use o processamento FF para trabalho em feriado."})
    units = _fc_units_for_date(assignment.assignment_date)
    source_type = FC_SOURCE_CODES[assignment.code]
    existing = _existing_fc_credits(assignment.military_id, source_type, assignment.assignment_date, assignment.code)
    created = []
    try:
        for unit_number in range(1, units + 1):
            if any(credit.unit_number == unit_number for credit in existing):
                continue
            credit = _new_fc_credit(
                military_id=assignment.military_id,
                source_type=source_type,
                source_assignment_id=assignment.id,
                source_schedule_version_id=assignment.schedule_version_id,
                source_service_date=assignment.assignment_date,
                source_service_code=assignment.code,
                unit_number=unit_number,
                units_from_source=units,
                acquired_date=assignment.assignment_date,
                notes=notes,
            )
            db.session.add(credit)
            db.session.flush()
            _add_fc_event(credit, CompensatoryLeaveCreditEventType.CREATED.value, None, credit.status, None, None, "Direito FC criado a partir de R/CR.")
            created.append(credit)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return created


def confirm_fr_from_assignment(assignment: Assignment, notes: str | None = None) -> RescheduledRestCredit:
    rest_type = _eligible_fr_rest_type(assignment)
    if rest_type is None:
        raise CompensationServiceError("Atribuicao sem direito FR.", {"origin": "FR exige AT/PO/PT em DS ou DC."})
    existing = RescheduledRestCredit.query.filter_by(
        military_id=assignment.military_id,
        original_rest_date=assignment.assignment_date,
        original_rest_type=rest_type,
    ).one_or_none()
    if existing is not None:
        return existing
    try:
        credit = RescheduledRestCredit(
            military_id=assignment.military_id,
            source_assignment_id=assignment.id,
            source_schedule_version_id=assignment.schedule_version_id,
            original_rest_date=assignment.assignment_date,
            original_rest_type=rest_type,
            source_service_code=assignment.code,
            status=RescheduledRestCreditStatus.PENDING.value,
            notes=_optional_text(notes),
        )
        db.session.add(credit)
        db.session.flush()
        _add_fr_event(credit, RescheduledRestCreditEventType.CREATED.value, None, credit.status, None, None, "Folga reagendada criada por servico em DS/DC.")
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return credit


def create_commander_discretionary_credit(payload: dict) -> list[CompensatoryLeaveCredit]:
    military_id = _parse_int(payload.get("military_id"), "military_id", "Escolha o militar.")
    military = db.session.get(Military, military_id)
    if military is None:
        raise CompensationServiceError("Militar inexistente.", {"military_id": "Escolha um militar valido."})
    acquired_date = _parse_date(payload.get("acquired_date"), "acquired_date", "Indique a data de aquisicao.")
    units = _parse_int(payload.get("units"), "units", "Indique um numero inteiro de FC.")
    if units <= 0:
        raise CompensationServiceError("Unidades invalidas.", {"units": "O numero de FC deve ser positivo."})
    reason = _required_text(payload.get("commander_reason"), "commander_reason", "Indique o motivo da decisao.")
    notes = _optional_text(payload.get("notes"))
    created = []
    try:
        for unit_number in range(1, units + 1):
            credit = _new_fc_credit(
                military_id=military.id,
                source_type=CompensatoryLeaveSourceType.COMMANDER_DISCRETION.value,
                source_assignment_id=None,
                source_schedule_version_id=None,
                source_service_date=acquired_date,
                source_service_code=None,
                unit_number=unit_number,
                units_from_source=units,
                acquired_date=acquired_date,
                notes=notes,
                commander_reason=reason,
            )
            db.session.add(credit)
            db.session.flush()
            _add_fc_event(credit, CompensatoryLeaveCreditEventType.CREATED.value, None, credit.status, None, None, "Direito FC criado por decisao de comando.", reason=reason)
            created.append(credit)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return created


def schedule_fc_credit(credit: CompensatoryLeaveCredit, schedule_version: ScheduleVersion, scheduled_date: date, notes: str | None = None) -> Assignment:
    return _schedule_fc_credit(credit, schedule_version, scheduled_date, notes, CompensatoryLeaveCreditEventType.SCHEDULED.value, AVAILABLE_FC_STATUSES)


def reschedule_fc_credit(credit: CompensatoryLeaveCredit, schedule_version: ScheduleVersion, scheduled_date: date, notes: str | None = None) -> Assignment:
    if credit.status not in {CompensatoryLeaveCreditStatus.SCHEDULED.value, CompensatoryLeaveCreditStatus.RESCHEDULED.value}:
        raise CompensationServiceError("Apenas FC agendada pode ser reagendada.", {"status": "A FC nao esta agendada."})
    _clear_linked_fc_assignment(credit, "Reagendamento de FC.")
    db.session.flush()
    return _schedule_fc_credit(
        credit,
        schedule_version,
        scheduled_date,
        notes,
        CompensatoryLeaveCreditEventType.RESCHEDULED.value,
        {CompensatoryLeaveCreditStatus.SCHEDULED.value, CompensatoryLeaveCreditStatus.RESCHEDULED.value},
    )


def cancel_fc_schedule(credit: CompensatoryLeaveCredit, reason: str | None = None, today: date | None = None) -> CompensatoryLeaveCredit:
    if credit.status not in {CompensatoryLeaveCreditStatus.SCHEDULED.value, CompensatoryLeaveCreditStatus.RESCHEDULED.value}:
        raise CompensationServiceError("Apenas FC agendada pode cancelar agendamento.", {"status": "A FC nao esta agendada."})
    previous_status = credit.status
    previous_date = credit.scheduled_date
    try:
        _clear_linked_fc_assignment(credit, reason or "Cancelamento do agendamento de FC.")
        current = today or utc_now().date()
        credit.status = CompensatoryLeaveCreditStatus.EXPIRED.value if current > credit.expires_on else CompensatoryLeaveCreditStatus.PENDING.value
        credit.scheduled_date = None
        credit.scheduled_at = None
        credit.effective_date = None
        credit.expiry_protected_at = None
        _add_fc_event(credit, CompensatoryLeaveCreditEventType.SCHEDULE_CANCELLED.value, previous_status, credit.status, previous_date, None, reason or "Agendamento de FC cancelado.")
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return credit


def cancel_fc_right(credit: CompensatoryLeaveCredit, reason: str | None) -> CompensatoryLeaveCredit:
    if credit.status == CompensatoryLeaveCreditStatus.USED.value:
        raise CompensationServiceError("FC ja gozada.", {"status": "Uma FC gozada nao pode ser cancelada."})
    reason = _required_text(reason, "reason", "Indique o motivo do cancelamento do direito.")
    previous_status = credit.status
    previous_date = credit.scheduled_date
    try:
        if credit.status in {CompensatoryLeaveCreditStatus.SCHEDULED.value, CompensatoryLeaveCreditStatus.RESCHEDULED.value}:
            _clear_linked_fc_assignment(credit, reason)
        credit.status = CompensatoryLeaveCreditStatus.CANCELLED.value
        credit.scheduled_date = None
        credit.effective_date = None
        credit.cancellation_reason = reason
        _add_fc_event(credit, CompensatoryLeaveCreditEventType.CANCELLED.value, previous_status, credit.status, previous_date, None, reason, reason=reason)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return credit


def schedule_fr_credit(credit: RescheduledRestCredit, schedule_version: ScheduleVersion, scheduled_date: date, notes: str | None = None) -> Assignment:
    return _schedule_fr_credit(credit, schedule_version, scheduled_date, notes, RescheduledRestCreditEventType.SCHEDULED.value, AVAILABLE_FR_STATUSES)


def reschedule_fr_credit(credit: RescheduledRestCredit, schedule_version: ScheduleVersion, scheduled_date: date, notes: str | None = None) -> Assignment:
    if credit.status not in {RescheduledRestCreditStatus.SCHEDULED.value, RescheduledRestCreditStatus.RESCHEDULED.value}:
        raise CompensationServiceError("Apenas FR agendada pode ser reagendada.", {"status": "A FR nao esta agendada."})
    _clear_linked_fr_assignment(credit, "Reagendamento de FR.")
    db.session.flush()
    return _schedule_fr_credit(
        credit,
        schedule_version,
        scheduled_date,
        notes,
        RescheduledRestCreditEventType.RESCHEDULED.value,
        {RescheduledRestCreditStatus.SCHEDULED.value, RescheduledRestCreditStatus.RESCHEDULED.value},
    )


def cancel_fr_schedule(credit: RescheduledRestCredit, reason: str | None = None) -> RescheduledRestCredit:
    if credit.status not in {RescheduledRestCreditStatus.SCHEDULED.value, RescheduledRestCreditStatus.RESCHEDULED.value}:
        raise CompensationServiceError("Apenas FR agendada pode cancelar agendamento.", {"status": "A FR nao esta agendada."})
    previous_status = credit.status
    previous_date = credit.scheduled_date
    try:
        _clear_linked_fr_assignment(credit, reason or "Cancelamento do agendamento de FR.")
        credit.status = RescheduledRestCreditStatus.PENDING.value
        credit.scheduled_date = None
        credit.effective_date = None
        _add_fr_event(credit, RescheduledRestCreditEventType.SCHEDULE_CANCELLED.value, previous_status, credit.status, previous_date, None, reason or "Agendamento de FR cancelado.")
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return credit


def confirm_fr_used(credit: RescheduledRestCredit, description: str | None = None) -> RescheduledRestCredit:
    if credit.status not in {RescheduledRestCreditStatus.SCHEDULED.value, RescheduledRestCreditStatus.RESCHEDULED.value}:
        raise CompensationServiceError("Apenas FR agendada pode ser confirmada como gozada.", {"status": "A FR nao esta agendada."})
    if _linked_visible_fr_assignment(credit) is None:
        raise CompensationServiceError("FR sem celula correspondente.", {"assignment": "Nao existe celula FR visivel ligada ao direito."})
    previous_status = credit.status
    try:
        credit.status = RescheduledRestCreditStatus.USED.value
        credit.effective_date = credit.scheduled_date
        _add_fr_event(credit, RescheduledRestCreditEventType.USED.value, previous_status, credit.status, credit.scheduled_date, credit.scheduled_date, description or "Gozo de FR confirmado.")
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return credit


def cancel_fr_right(credit: RescheduledRestCredit, reason: str | None) -> RescheduledRestCredit:
    reason = _required_text(reason, "reason", "Indique o motivo do cancelamento do direito.")
    previous_status = credit.status
    previous_date = credit.scheduled_date
    try:
        if credit.status in {RescheduledRestCreditStatus.SCHEDULED.value, RescheduledRestCreditStatus.RESCHEDULED.value}:
            _clear_linked_fr_assignment(credit, reason)
        credit.status = RescheduledRestCreditStatus.CANCELLED.value
        credit.scheduled_date = None
        credit.effective_date = None
        credit.cancellation_reason = reason
        _add_fr_event(credit, RescheduledRestCreditEventType.CANCELLED.value, previous_status, credit.status, previous_date, None, reason, reason=reason)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return credit


def fc_balance_by_military() -> list[CompensatoryLeaveBalance]:
    rows = _status_counts(CompensatoryLeaveCredit)
    return [
        CompensatoryLeaveBalance(
            military=military,
            acquired=sum(statuses.values()),
            pending=statuses.get(CompensatoryLeaveCreditStatus.PENDING.value, 0),
            scheduled=statuses.get(CompensatoryLeaveCreditStatus.SCHEDULED.value, 0),
            rescheduled=statuses.get(CompensatoryLeaveCreditStatus.RESCHEDULED.value, 0),
            used=statuses.get(CompensatoryLeaveCreditStatus.USED.value, 0),
            cancelled=statuses.get(CompensatoryLeaveCreditStatus.CANCELLED.value, 0),
            expired=statuses.get(CompensatoryLeaveCreditStatus.EXPIRED.value, 0),
        )
        for military, statuses in rows
    ]


def fr_balance_by_military() -> list[RescheduledRestBalance]:
    rows = _status_counts(RescheduledRestCredit)
    return [
        RescheduledRestBalance(
            military=military,
            acquired=sum(statuses.values()),
            pending=statuses.get(RescheduledRestCreditStatus.PENDING.value, 0),
            scheduled=statuses.get(RescheduledRestCreditStatus.SCHEDULED.value, 0),
            rescheduled=statuses.get(RescheduledRestCreditStatus.RESCHEDULED.value, 0),
            used=statuses.get(RescheduledRestCreditStatus.USED.value, 0),
            cancelled=statuses.get(RescheduledRestCreditStatus.CANCELLED.value, 0),
        )
        for military, statuses in rows
    ]


class CompensationMaintenanceService:
    def process(self, today: date | None = None) -> dict[str, int]:
        current = today or utc_now().date()
        summary = {"expired": 0, "auto_used": 0}
        try:
            summary["expired"] = self._expire_pending(current)
            summary["auto_used"] = self._auto_use_scheduled(current)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return summary

    def _expire_pending(self, current: date) -> int:
        count = 0
        credits = CompensatoryLeaveCredit.query.filter(
            CompensatoryLeaveCredit.status == CompensatoryLeaveCreditStatus.PENDING.value,
            CompensatoryLeaveCredit.expires_on < current,
            CompensatoryLeaveCredit.expiry_protected_at.is_(None),
        ).all()
        for credit in credits:
            previous_status = credit.status
            credit.status = CompensatoryLeaveCreditStatus.EXPIRED.value
            _add_fc_event(credit, CompensatoryLeaveCreditEventType.EXPIRED.value, previous_status, credit.status, None, None, "FC expirada automaticamente.", is_automatic=True)
            count += 1
        return count

    def _auto_use_scheduled(self, current: date) -> int:
        count = 0
        credits = CompensatoryLeaveCredit.query.filter(
            CompensatoryLeaveCredit.status.in_([CompensatoryLeaveCreditStatus.SCHEDULED.value, CompensatoryLeaveCreditStatus.RESCHEDULED.value]),
            CompensatoryLeaveCredit.scheduled_date < current,
        ).all()
        for credit in credits:
            assignment = _linked_visible_fc_assignment(credit, include_official=True)
            if assignment is None or not _assignment_belongs_to_official_version(assignment):
                continue
            previous_status = credit.status
            credit.status = CompensatoryLeaveCreditStatus.USED.value
            credit.effective_date = credit.scheduled_date
            _add_fc_event(credit, CompensatoryLeaveCreditEventType.AUTO_USED.value, previous_status, credit.status, credit.scheduled_date, credit.scheduled_date, "Gozo de FC confirmado automaticamente por versao oficial.", is_automatic=True)
            count += 1
        return count


def _fc_potential_for_assignment(assignment: Assignment, holidays: set[date]) -> PotentialCompensatoryLeave | None:
    source_type = FC_SOURCE_CODES[assignment.code]
    units = _fc_units_for_date(assignment.assignment_date)
    existing = _existing_fc_credits(assignment.military_id, source_type, assignment.assignment_date, assignment.code)
    return PotentialCompensatoryLeave(
        assignment=assignment,
        source_type=source_type,
        units=units,
        existing_credits=existing,
        is_holiday=assignment.assignment_date in holidays,
    )


def _fr_potential_for_assignment(assignment: Assignment) -> PotentialRescheduledRest | None:
    rest_type = _eligible_fr_rest_type(assignment)
    if rest_type is None:
        return None
    existing = RescheduledRestCredit.query.filter_by(
        military_id=assignment.military_id,
        original_rest_date=assignment.assignment_date,
        original_rest_type=rest_type,
    ).one_or_none()
    return PotentialRescheduledRest(assignment=assignment, original_rest_type=rest_type, existing_credit=existing)


def _schedule_fc_credit(
    credit: CompensatoryLeaveCredit,
    schedule_version: ScheduleVersion,
    scheduled_date: date,
    notes: str | None,
    event_type: str,
    allowed_statuses: set[str],
) -> Assignment:
    previous_status = credit.status
    previous_date = credit.scheduled_date
    _validate_schedule_target(credit.military, schedule_version, scheduled_date, allowed_statuses, credit.status, "FC")
    if credit.status == CompensatoryLeaveCreditStatus.EXPIRED.value:
        raise CompensationServiceError("FC expirada.", {"status": "A FC expirada nao pode ser agendada."})
    try:
        assignment = _create_leave_assignment(schedule_version, credit.military_id, scheduled_date, "FC", notes)
        assignment.compensatory_leave_credit_id = credit.id
        now = utc_now()
        credit.status = CompensatoryLeaveCreditStatus.RESCHEDULED.value if event_type == CompensatoryLeaveCreditEventType.RESCHEDULED.value else CompensatoryLeaveCreditStatus.SCHEDULED.value
        credit.scheduled_date = scheduled_date
        credit.scheduled_at = now
        credit.effective_date = None
        if now.date() <= credit.expires_on or credit.expiry_protected_at is not None:
            credit.expiry_protected_at = credit.expiry_protected_at or now
        touch_version_content(schedule_version)
        _add_fc_event(credit, event_type, previous_status, credit.status, previous_date, scheduled_date, "FC agendada na escala.")
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return assignment


def _schedule_fr_credit(
    credit: RescheduledRestCredit,
    schedule_version: ScheduleVersion,
    scheduled_date: date,
    notes: str | None,
    event_type: str,
    allowed_statuses: set[str],
) -> Assignment:
    previous_status = credit.status
    previous_date = credit.scheduled_date
    _validate_schedule_target(credit.military, schedule_version, scheduled_date, allowed_statuses, credit.status, "FR")
    try:
        assignment = _create_leave_assignment(schedule_version, credit.military_id, scheduled_date, "FR", notes)
        assignment.rescheduled_rest_credit_id = credit.id
        credit.status = RescheduledRestCreditStatus.RESCHEDULED.value if event_type == RescheduledRestCreditEventType.RESCHEDULED.value else RescheduledRestCreditStatus.SCHEDULED.value
        credit.scheduled_date = scheduled_date
        credit.effective_date = None
        touch_version_content(schedule_version)
        _add_fr_event(credit, event_type, previous_status, credit.status, previous_date, scheduled_date, "FR agendada na escala.")
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return assignment


def _validate_schedule_target(
    military: Military,
    schedule_version: ScheduleVersion,
    scheduled_date: date,
    allowed_statuses: set[str],
    current_status: str,
    code: str,
) -> None:
    if current_status not in allowed_statuses:
        raise CompensationServiceError("Estado nao permite agendamento.", {"status": f"A {code} nao esta disponivel para agendamento."})
    policy = ScheduleVersionPolicy(schedule_version)
    if code == "FC" and not policy.can_schedule_fc():
        raise CompensationServiceError("Versao nao editavel.", {"status": "A FC so pode ser agendada em versao DRAFT."})
    if code == "FR" and not policy.can_schedule_fr():
        raise CompensationServiceError("Versao nao editavel.", {"status": "A FR so pode ser agendada em versao DRAFT."})
    if not _date_belongs_to_version(schedule_version, scheduled_date):
        raise CompensationServiceError("Data fora do mes.", {"scheduled_date": "A data nao pertence ao mes da versao."})
    if not _military_in_period(military, scheduled_date):
        raise CompensationServiceError("Militar fora do periodo.", {"military": "O militar esta fora do periodo de efetividade."})
    existing = Assignment.query.filter_by(
        schedule_version_id=schedule_version.id,
        military_id=military.id,
        assignment_date=scheduled_date,
    ).one_or_none()
    if existing is not None and existing.is_visible:
        raise CompensationServiceError("Celula ocupada.", {"assignment": "A data ja possui atribuicao visivel. Ajuste a escala antes de agendar compensacao."})
    if _has_unavailability(military.id, scheduled_date):
        raise CompensationServiceError("Indisponibilidade na data.", {"unavailability": "A data possui indisponibilidade ativa."})
    if _cycle_code_for_military(military, scheduled_date) in {"DS", "DC"}:
        raise CompensationServiceError("Data coincide com DS/DC.", {"cycle": f"A {code} nao deve ser agendada em DS/DC."})


def _create_leave_assignment(schedule_version: ScheduleVersion, military_id: int, scheduled_date: date, code: str, notes: str | None) -> Assignment:
    assignment = Assignment.query.filter_by(
        schedule_version_id=schedule_version.id,
        military_id=military_id,
        assignment_date=scheduled_date,
    ).one_or_none()
    if assignment is None:
        assignment = Assignment(
            schedule_version_id=schedule_version.id,
            military_id=military_id,
            assignment_date=scheduled_date,
            code=code,
            source=AssignmentSource.MANUAL.value,
            is_manual=True,
            is_locked=True,
            has_override=False,
            notes=_optional_text(notes),
            duration_minutes=480,
            is_cleared=False,
        )
        db.session.add(assignment)
        _add_assignment_change(assignment, AssignmentChangeType.CREATED.value, None, code, None, True, None, False, notes)
        return assignment
    previous_code = assignment.code
    previous_locked = assignment.is_locked
    previous_override = assignment.has_override
    assignment.code = code
    assignment.source = AssignmentSource.MANUAL.value
    assignment.is_manual = True
    assignment.is_locked = True
    assignment.has_override = False
    assignment.override_reason = None
    assignment.notes = _optional_text(notes)
    assignment.duration_minutes = 480
    assignment.is_cleared = False
    _add_assignment_change(assignment, AssignmentChangeType.UPDATED.value, previous_code, code, previous_locked, True, previous_override, False, notes)
    return assignment


def _clear_linked_fc_assignment(credit: CompensatoryLeaveCredit, reason: str) -> None:
    _clear_assignments(_linked_visible_fc_assignments(credit), reason)


def _clear_linked_fr_assignment(credit: RescheduledRestCredit, reason: str) -> None:
    _clear_assignments(_linked_visible_fr_assignments(credit), reason)


def _clear_assignments(assignments: list[Assignment], reason: str) -> None:
    touched_versions = set()
    for assignment in assignments:
        if not ScheduleVersionPolicy(assignment.schedule_version).can_edit():
            raise CompensationServiceError("Versao nao editavel.", {"status": "A celula ligada esta numa versao que nao permite edicao."})
        previous_code = assignment.code
        previous_override = assignment.has_override
        assignment.code = None
        assignment.has_override = False
        assignment.override_reason = None
        assignment.is_cleared = True
        assignment.compensatory_leave_credit_id = None
        assignment.rescheduled_rest_credit_id = None
        _add_assignment_change(assignment, AssignmentChangeType.CLEARED.value, previous_code, None, assignment.is_locked, assignment.is_locked, previous_override, False, reason)
        if assignment.schedule_version_id not in touched_versions:
            touch_version_content(assignment.schedule_version)
            touched_versions.add(assignment.schedule_version_id)


def _linked_visible_fc_assignment(credit: CompensatoryLeaveCredit, include_official: bool = False) -> Assignment | None:
    assignments = _linked_visible_fc_assignments(credit, include_official=include_official)
    return assignments[0] if assignments else None


def _linked_visible_fc_assignments(credit: CompensatoryLeaveCredit, include_official: bool = False) -> list[Assignment]:
    if credit.scheduled_date is None:
        return []
    query = Assignment.query.filter_by(
        compensatory_leave_credit_id=credit.id,
        military_id=credit.military_id,
        assignment_date=credit.scheduled_date,
        code="FC",
        is_cleared=False,
    ).join(ScheduleVersion, Assignment.schedule_version_id == ScheduleVersion.id)
    if not include_official:
        query = query.filter(ScheduleVersion.status == ScheduleMonthStatus.DRAFT.value)
    return query.order_by(Assignment.schedule_version_id.desc(), Assignment.id.desc()).all()


def _linked_visible_fr_assignment(credit: RescheduledRestCredit) -> Assignment | None:
    assignments = _linked_visible_fr_assignments(credit)
    return assignments[0] if assignments else None


def _linked_visible_fr_assignments(credit: RescheduledRestCredit) -> list[Assignment]:
    if credit.scheduled_date is None:
        return []
    return Assignment.query.filter_by(
        rescheduled_rest_credit_id=credit.id,
        military_id=credit.military_id,
        assignment_date=credit.scheduled_date,
        code="FR",
        is_cleared=False,
    ).join(ScheduleVersion, Assignment.schedule_version_id == ScheduleVersion.id).filter(
        ScheduleVersion.status == ScheduleMonthStatus.DRAFT.value
    ).order_by(Assignment.schedule_version_id.desc(), Assignment.id.desc()).all()


def _assignment_belongs_to_official_version(assignment: Assignment) -> bool:
    version = assignment.schedule_version
    month = version.schedule_month
    return version.status in {ScheduleMonthStatus.PUBLISHED.value, ScheduleMonthStatus.CLOSED.value} and month.published_version_id == version.id


def _new_fc_credit(**kwargs) -> CompensatoryLeaveCredit:
    acquired_date = kwargs["acquired_date"]
    return CompensatoryLeaveCredit(
        **kwargs,
        minutes=480,
        expires_on=date(acquired_date.year, 12, 31),
        status=CompensatoryLeaveCreditStatus.PENDING.value,
    )


def _existing_fc_credits(military_id: int, source_type: str, source_date: date, source_code: str) -> list[CompensatoryLeaveCredit]:
    return CompensatoryLeaveCredit.query.filter_by(
        military_id=military_id,
        source_type=source_type,
        source_service_date=source_date,
        source_service_code=source_code,
    ).order_by(CompensatoryLeaveCredit.unit_number.asc()).all()


def _fc_units_for_date(service_date: date) -> int:
    return 2 if service_date.weekday() >= 5 else 1


def _eligible_fr_rest_type(assignment: Assignment) -> str | None:
    if assignment is None or not assignment.is_visible or assignment.code not in FR_SOURCE_CODES:
        return None
    rest_type = _cycle_code_for_military(assignment.military, assignment.assignment_date)
    if rest_type not in {"DS", "DC"}:
        return None
    return rest_type


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


def _date_belongs_to_version(schedule_version: ScheduleVersion, assignment_date: date) -> bool:
    last_day = monthrange(schedule_version.schedule_month.year, schedule_version.schedule_month.month)[1]
    return date(schedule_version.schedule_month.year, schedule_version.schedule_month.month, 1) <= assignment_date <= date(
        schedule_version.schedule_month.year,
        schedule_version.schedule_month.month,
        last_day,
    )


def _military_in_period(military: Military, assignment_date: date) -> bool:
    return military.start_date <= assignment_date and (military.end_date is None or assignment_date <= military.end_date)


def _is_active_holiday(current: date) -> bool:
    return Holiday.query.filter_by(holiday_date=current, is_active=True).first() is not None


def _version_start(schedule_version: ScheduleVersion) -> date:
    return date(schedule_version.schedule_month.year, schedule_version.schedule_month.month, 1)


def _version_end(schedule_version: ScheduleVersion) -> date:
    last_day = monthrange(schedule_version.schedule_month.year, schedule_version.schedule_month.month)[1]
    return date(schedule_version.schedule_month.year, schedule_version.schedule_month.month, last_day)


def _status_counts(model) -> list[tuple[Military, dict[str, int]]]:
    militaries = Military.query.order_by(Military.name.asc(), Military.nim.asc()).all()
    counts = (
        db.session.query(model.military_id, model.status, func.count(model.id))
        .group_by(model.military_id, model.status)
        .all()
    )
    by_military: dict[int, dict[str, int]] = {}
    for military_id, status, count in counts:
        by_military.setdefault(military_id, {})[status] = count
    return [(military, by_military.get(military.id, {})) for military in militaries]


def _add_fc_event(
    credit: CompensatoryLeaveCredit,
    event_type: str,
    previous_status: str | None,
    new_status: str | None,
    previous_date: date | None,
    new_date: date | None,
    description: str,
    reason: str | None = None,
    is_automatic: bool = False,
) -> None:
    db.session.add(
        CompensatoryLeaveCreditEvent(
            credit=credit,
            event_type=event_type,
            previous_status=previous_status,
            new_status=new_status,
            previous_scheduled_date=previous_date,
            new_scheduled_date=new_date,
            description=description,
            reason=reason,
            is_automatic=is_automatic,
        )
    )


def _add_fr_event(
    credit: RescheduledRestCredit,
    event_type: str,
    previous_status: str | None,
    new_status: str | None,
    previous_date: date | None,
    new_date: date | None,
    description: str,
    reason: str | None = None,
    is_automatic: bool = False,
) -> None:
    db.session.add(
        RescheduledRestCreditEvent(
            credit=credit,
            event_type=event_type,
            previous_status=previous_status,
            new_status=new_status,
            previous_scheduled_date=previous_date,
            new_scheduled_date=new_date,
            description=description,
            reason=reason,
            is_automatic=is_automatic,
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


def _parse_date(value: str | None, field: str, message: str) -> date:
    try:
        return date.fromisoformat(value or "")
    except ValueError as exc:
        raise CompensationServiceError("Data invalida.", {field: message}) from exc


def _parse_int(value: str | None, field: str, message: str) -> int:
    if value is None or not str(value).isdigit():
        raise CompensationServiceError("Numero invalido.", {field: message})
    return int(value)


def _required_text(value: str | None, field: str, message: str) -> str:
    text = (value or "").strip()
    if not text:
        raise CompensationServiceError("Texto obrigatorio.", {field: message})
    return text


def _optional_text(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None
