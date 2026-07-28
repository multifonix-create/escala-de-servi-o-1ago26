from enum import StrEnum

from app.extensions import db
from app.models.military import utc_now


class HolidayScope(StrEnum):
    NATIONAL = "NATIONAL"
    MUNICIPAL = "MUNICIPAL"
    LOCAL = "LOCAL"
    INSTITUTIONAL = "INSTITUTIONAL"


class HolidayLeaveCreditStatus(StrEnum):
    PENDING = "PENDING"
    SCHEDULED = "SCHEDULED"
    USED = "USED"
    RESCHEDULED = "RESCHEDULED"
    CANCELLED = "CANCELLED"


class HolidayLeaveCreditEventType(StrEnum):
    CREATED = "CREATED"
    SCHEDULED = "SCHEDULED"
    RESCHEDULED = "RESCHEDULED"
    SCHEDULE_CANCELLED = "SCHEDULE_CANCELLED"
    USED = "USED"
    CANCELLED = "CANCELLED"
    NOTES_UPDATED = "NOTES_UPDATED"


ALLOWED_HOLIDAY_SCOPES = tuple(item.value for item in HolidayScope)
ALLOWED_HOLIDAY_LEAVE_CREDIT_STATUSES = tuple(item.value for item in HolidayLeaveCreditStatus)
ALLOWED_HOLIDAY_LEAVE_CREDIT_EVENT_TYPES = tuple(item.value for item in HolidayLeaveCreditEventType)

HOLIDAY_SCOPE_LABELS = {
    HolidayScope.NATIONAL.value: "Nacional",
    HolidayScope.MUNICIPAL.value: "Municipal",
    HolidayScope.LOCAL.value: "Local",
    HolidayScope.INSTITUTIONAL.value: "Institucional",
}

HOLIDAY_LEAVE_CREDIT_STATUS_LABELS = {
    HolidayLeaveCreditStatus.PENDING.value: "Pendente",
    HolidayLeaveCreditStatus.SCHEDULED.value: "Agendada",
    HolidayLeaveCreditStatus.USED.value: "Gozada",
    HolidayLeaveCreditStatus.RESCHEDULED.value: "Reagendada",
    HolidayLeaveCreditStatus.CANCELLED.value: "Cancelada",
}


class Holiday(db.Model):
    __tablename__ = "holidays"
    __table_args__ = (
        db.UniqueConstraint("holiday_date", "scope", name="uq_holidays_date_scope"),
        db.CheckConstraint(
            "scope in ('NATIONAL', 'MUNICIPAL', 'LOCAL', 'INSTITUTIONAL')",
            name="ck_holidays_scope",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    holiday_date = db.Column(db.Date, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    scope = db.Column(db.String(30), nullable=False, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    credits = db.relationship(
        "HolidayLeaveCredit",
        back_populates="holiday",
        order_by="HolidayLeaveCredit.created_at.asc(), HolidayLeaveCredit.id.asc()",
    )

    @property
    def scope_label(self) -> str:
        return HOLIDAY_SCOPE_LABELS.get(self.scope, self.scope)


class HolidayLeaveCredit(db.Model):
    __tablename__ = "holiday_leave_credits"
    __table_args__ = (
        db.UniqueConstraint("source_assignment_id", name="uq_holiday_leave_credits_source_assignment"),
        db.CheckConstraint(
            "status in ('PENDING', 'SCHEDULED', 'USED', 'RESCHEDULED', 'CANCELLED')",
            name="ck_holiday_leave_credits_status",
        ),
        db.CheckConstraint(
            "service_code in ('AT1', 'AT2', 'AT3', 'PO1', 'PO2', 'PO3', 'PT')",
            name="ck_holiday_leave_credits_service_code",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    military_id = db.Column(db.Integer, db.ForeignKey("militaries.id"), nullable=False, index=True)
    holiday_id = db.Column(db.Integer, db.ForeignKey("holidays.id"), nullable=False, index=True)
    source_assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"), nullable=False, index=True)
    source_schedule_version_id = db.Column(db.Integer, db.ForeignKey("schedule_versions.id"), nullable=False, index=True)
    source_generation_run_id = db.Column(db.Integer, db.ForeignKey("generation_runs.id"), nullable=True, index=True)
    service_date = db.Column(db.Date, nullable=False, index=True)
    service_code = db.Column(db.String(30), nullable=False, index=True)
    acquired_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    status = db.Column(
        db.String(30),
        nullable=False,
        default=HolidayLeaveCreditStatus.PENDING.value,
        index=True,
    )
    scheduled_date = db.Column(db.Date, nullable=True, index=True)
    effective_date = db.Column(db.Date, nullable=True, index=True)
    cancellation_reason = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    military = db.relationship("Military")
    holiday = db.relationship("Holiday", back_populates="credits")
    source_assignment = db.relationship("Assignment", foreign_keys=[source_assignment_id])
    source_schedule_version = db.relationship("ScheduleVersion", foreign_keys=[source_schedule_version_id])
    source_generation_run = db.relationship("GenerationRun", foreign_keys=[source_generation_run_id])
    events = db.relationship(
        "HolidayLeaveCreditEvent",
        back_populates="credit",
        order_by="HolidayLeaveCreditEvent.created_at.asc(), HolidayLeaveCreditEvent.id.asc()",
    )

    @property
    def status_label(self) -> str:
        return HOLIDAY_LEAVE_CREDIT_STATUS_LABELS.get(self.status, self.status)

    @property
    def is_available(self) -> bool:
        return self.status in {
            HolidayLeaveCreditStatus.PENDING.value,
            HolidayLeaveCreditStatus.RESCHEDULED.value,
        }


class HolidayLeaveCreditEvent(db.Model):
    __tablename__ = "holiday_leave_credit_events"
    __table_args__ = (
        db.CheckConstraint(
            "event_type in ('CREATED', 'SCHEDULED', 'RESCHEDULED', 'SCHEDULE_CANCELLED', 'USED', 'CANCELLED', 'NOTES_UPDATED')",
            name="ck_holiday_leave_credit_events_type",
        ),
        db.CheckConstraint(
            "previous_status is null or previous_status in ('PENDING', 'SCHEDULED', 'USED', 'RESCHEDULED', 'CANCELLED')",
            name="ck_holiday_leave_credit_events_previous_status",
        ),
        db.CheckConstraint(
            "new_status is null or new_status in ('PENDING', 'SCHEDULED', 'USED', 'RESCHEDULED', 'CANCELLED')",
            name="ck_holiday_leave_credit_events_new_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    credit_id = db.Column(db.Integer, db.ForeignKey("holiday_leave_credits.id"), nullable=False, index=True)
    event_type = db.Column(db.String(40), nullable=False, index=True)
    previous_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=True)
    previous_scheduled_date = db.Column(db.Date, nullable=True)
    new_scheduled_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    credit = db.relationship("HolidayLeaveCredit", back_populates="events")
