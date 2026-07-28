from enum import StrEnum

from app.extensions import db
from app.models.military import utc_now


class CompensatoryLeaveSourceType(StrEnum):
    RONDA = "RONDA"
    CONDUTOR_RONDANTE = "CONDUTOR_RONDANTE"
    COMMANDER_DISCRETION = "COMMANDER_DISCRETION"


class CompensatoryLeaveCreditStatus(StrEnum):
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    RESCHEDULED = "RESCHEDULED"
    USED = "USED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class CompensatoryLeaveCreditEventType(StrEnum):
    CREATED = "CREATED"
    SCHEDULED = "SCHEDULED"
    RESCHEDULED = "RESCHEDULED"
    SCHEDULE_CANCELLED = "SCHEDULE_CANCELLED"
    USED = "USED"
    AUTO_USED = "AUTO_USED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    NOTES_UPDATED = "NOTES_UPDATED"


class RescheduledRestCreditStatus(StrEnum):
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    RESCHEDULED = "RESCHEDULED"
    USED = "USED"
    CANCELLED = "CANCELLED"


class RescheduledRestCreditEventType(StrEnum):
    CREATED = "CREATED"
    SCHEDULED = "SCHEDULED"
    RESCHEDULED = "RESCHEDULED"
    SCHEDULE_CANCELLED = "SCHEDULE_CANCELLED"
    USED = "USED"
    CANCELLED = "CANCELLED"
    NOTES_UPDATED = "NOTES_UPDATED"


ALLOWED_COMPENSATORY_LEAVE_SOURCE_TYPES = tuple(item.value for item in CompensatoryLeaveSourceType)
ALLOWED_COMPENSATORY_LEAVE_CREDIT_STATUSES = tuple(item.value for item in CompensatoryLeaveCreditStatus)
ALLOWED_COMPENSATORY_LEAVE_CREDIT_EVENT_TYPES = tuple(item.value for item in CompensatoryLeaveCreditEventType)
ALLOWED_RESCHEDULED_REST_CREDIT_STATUSES = tuple(item.value for item in RescheduledRestCreditStatus)
ALLOWED_RESCHEDULED_REST_CREDIT_EVENT_TYPES = tuple(item.value for item in RescheduledRestCreditEventType)

COMPENSATORY_LEAVE_SOURCE_TYPE_LABELS = {
    CompensatoryLeaveSourceType.RONDA.value: "Ronda",
    CompensatoryLeaveSourceType.CONDUTOR_RONDANTE.value: "Condutor rondante",
    CompensatoryLeaveSourceType.COMMANDER_DISCRETION.value: "Decisao de comando",
}

COMPENSATORY_LEAVE_CREDIT_STATUS_LABELS = {
    CompensatoryLeaveCreditStatus.PENDING.value: "Pendente",
    CompensatoryLeaveCreditStatus.SCHEDULED.value: "Agendada",
    CompensatoryLeaveCreditStatus.RESCHEDULED.value: "Reagendada",
    CompensatoryLeaveCreditStatus.USED.value: "Gozada",
    CompensatoryLeaveCreditStatus.CANCELLED.value: "Cancelada",
    CompensatoryLeaveCreditStatus.EXPIRED.value: "Expirada",
}

RESCHEDULED_REST_CREDIT_STATUS_LABELS = {
    RescheduledRestCreditStatus.PENDING.value: "Pendente",
    RescheduledRestCreditStatus.SCHEDULED.value: "Agendada",
    RescheduledRestCreditStatus.RESCHEDULED.value: "Reagendada",
    RescheduledRestCreditStatus.USED.value: "Gozada",
    RescheduledRestCreditStatus.CANCELLED.value: "Cancelada",
}


class CompensatoryLeaveCredit(db.Model):
    __tablename__ = "compensatory_leave_credits"
    __table_args__ = (
        db.CheckConstraint("source_type in ('RONDA', 'CONDUTOR_RONDANTE', 'COMMANDER_DISCRETION')", name="ck_compensatory_leave_credits_source_type"),
        db.CheckConstraint("status in ('PENDING', 'SCHEDULED', 'RESCHEDULED', 'USED', 'CANCELLED', 'EXPIRED')", name="ck_compensatory_leave_credits_status"),
        db.CheckConstraint("minutes = 480", name="ck_compensatory_leave_credits_minutes"),
        db.CheckConstraint("unit_number >= 1", name="ck_compensatory_leave_credits_unit_number"),
        db.CheckConstraint("units_from_source >= 1", name="ck_compensatory_leave_credits_units_from_source"),
        db.UniqueConstraint("military_id", "source_type", "source_service_date", "source_service_code", "unit_number", name="uq_compensatory_leave_credits_source_unit"),
    )

    id = db.Column(db.Integer, primary_key=True)
    military_id = db.Column(db.Integer, db.ForeignKey("militaries.id"), nullable=False, index=True)
    source_type = db.Column(db.String(40), nullable=False, index=True)
    source_assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"), nullable=True, index=True)
    source_schedule_version_id = db.Column(db.Integer, db.ForeignKey("schedule_versions.id"), nullable=True, index=True)
    source_service_date = db.Column(db.Date, nullable=False, index=True)
    source_service_code = db.Column(db.String(30), nullable=True, index=True)
    unit_number = db.Column(db.Integer, nullable=False)
    units_from_source = db.Column(db.Integer, nullable=False)
    minutes = db.Column(db.Integer, nullable=False, default=480)
    acquired_date = db.Column(db.Date, nullable=False, index=True)
    expires_on = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default=CompensatoryLeaveCreditStatus.PENDING.value, index=True)
    scheduled_date = db.Column(db.Date, nullable=True, index=True)
    scheduled_at = db.Column(db.DateTime(timezone=True), nullable=True)
    effective_date = db.Column(db.Date, nullable=True, index=True)
    expiry_protected_at = db.Column(db.DateTime(timezone=True), nullable=True)
    cancellation_reason = db.Column(db.Text, nullable=True)
    commander_reason = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    military = db.relationship("Military")
    source_assignment = db.relationship("Assignment", foreign_keys=[source_assignment_id])
    source_schedule_version = db.relationship("ScheduleVersion", foreign_keys=[source_schedule_version_id])
    events = db.relationship("CompensatoryLeaveCreditEvent", back_populates="credit", order_by="CompensatoryLeaveCreditEvent.created_at.asc(), CompensatoryLeaveCreditEvent.id.asc()")


class CompensatoryLeaveCreditEvent(db.Model):
    __tablename__ = "compensatory_leave_credit_events"
    __table_args__ = (
        db.CheckConstraint("event_type in ('CREATED', 'SCHEDULED', 'RESCHEDULED', 'SCHEDULE_CANCELLED', 'USED', 'AUTO_USED', 'CANCELLED', 'EXPIRED', 'NOTES_UPDATED')", name="ck_compensatory_leave_credit_events_type"),
        db.CheckConstraint("previous_status is null or previous_status in ('PENDING', 'SCHEDULED', 'RESCHEDULED', 'USED', 'CANCELLED', 'EXPIRED')", name="ck_compensatory_leave_credit_events_previous_status"),
        db.CheckConstraint("new_status is null or new_status in ('PENDING', 'SCHEDULED', 'RESCHEDULED', 'USED', 'CANCELLED', 'EXPIRED')", name="ck_compensatory_leave_credit_events_new_status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    credit_id = db.Column(db.Integer, db.ForeignKey("compensatory_leave_credits.id"), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    previous_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=True)
    previous_scheduled_date = db.Column(db.Date, nullable=True)
    new_scheduled_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)
    reason = db.Column(db.Text, nullable=True)
    is_automatic = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    credit = db.relationship("CompensatoryLeaveCredit", back_populates="events")


class RescheduledRestCredit(db.Model):
    __tablename__ = "rescheduled_rest_credits"
    __table_args__ = (
        db.CheckConstraint("original_rest_type in ('DS', 'DC')", name="ck_rescheduled_rest_credits_rest_type"),
        db.CheckConstraint("source_service_code in ('AT1', 'AT2', 'AT3', 'PO1', 'PO2', 'PO3', 'PT')", name="ck_rescheduled_rest_credits_source_service_code"),
        db.CheckConstraint("status in ('PENDING', 'SCHEDULED', 'RESCHEDULED', 'USED', 'CANCELLED')", name="ck_rescheduled_rest_credits_status"),
        db.UniqueConstraint("military_id", "original_rest_date", "original_rest_type", name="uq_rescheduled_rest_credits_origin_day"),
    )

    id = db.Column(db.Integer, primary_key=True)
    military_id = db.Column(db.Integer, db.ForeignKey("militaries.id"), nullable=False, index=True)
    source_assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"), nullable=True, index=True)
    source_schedule_version_id = db.Column(db.Integer, db.ForeignKey("schedule_versions.id"), nullable=True, index=True)
    original_rest_date = db.Column(db.Date, nullable=False, index=True)
    original_rest_type = db.Column(db.String(2), nullable=False, index=True)
    source_service_code = db.Column(db.String(30), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, default=RescheduledRestCreditStatus.PENDING.value, index=True)
    scheduled_date = db.Column(db.Date, nullable=True, index=True)
    effective_date = db.Column(db.Date, nullable=True, index=True)
    cancellation_reason = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    military = db.relationship("Military")
    source_assignment = db.relationship("Assignment", foreign_keys=[source_assignment_id])
    source_schedule_version = db.relationship("ScheduleVersion", foreign_keys=[source_schedule_version_id])
    events = db.relationship("RescheduledRestCreditEvent", back_populates="credit", order_by="RescheduledRestCreditEvent.created_at.asc(), RescheduledRestCreditEvent.id.asc()")


class RescheduledRestCreditEvent(db.Model):
    __tablename__ = "rescheduled_rest_credit_events"
    __table_args__ = (
        db.CheckConstraint("event_type in ('CREATED', 'SCHEDULED', 'RESCHEDULED', 'SCHEDULE_CANCELLED', 'USED', 'CANCELLED', 'NOTES_UPDATED')", name="ck_rescheduled_rest_credit_events_type"),
        db.CheckConstraint("previous_status is null or previous_status in ('PENDING', 'SCHEDULED', 'RESCHEDULED', 'USED', 'CANCELLED')", name="ck_rescheduled_rest_credit_events_previous_status"),
        db.CheckConstraint("new_status is null or new_status in ('PENDING', 'SCHEDULED', 'RESCHEDULED', 'USED', 'CANCELLED')", name="ck_rescheduled_rest_credit_events_new_status"),
    )

    id = db.Column(db.Integer, primary_key=True)
    credit_id = db.Column(db.Integer, db.ForeignKey("rescheduled_rest_credits.id"), nullable=False, index=True)
    event_type = db.Column(db.String(50), nullable=False, index=True)
    previous_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=True)
    previous_scheduled_date = db.Column(db.Date, nullable=True)
    new_scheduled_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)
    reason = db.Column(db.Text, nullable=True)
    is_automatic = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    credit = db.relationship("RescheduledRestCredit", back_populates="events")
