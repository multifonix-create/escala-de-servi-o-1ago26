from enum import StrEnum

from app.extensions import db
from app.models.military import utc_now


class UnavailabilityCode(StrEnum):
    LF = "LF"
    LP = "LP"
    BM = "BM"
    LC = "LC"
    LN = "LN"
    DIL = "DIL"
    TRIB = "TRIB"
    INQ = "INQ"
    FORMACAO = "FORMACAO"
    TIRO = "TIRO"
    OUTRA = "OUTRA"


class UnavailabilityStatus(StrEnum):
    PLANNED = "PLANNED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class CompensationStatus(StrEnum):
    NOT_APPLICABLE = "NOT_APPLICABLE"
    PENDING_DECISION = "PENDING_DECISION"
    GENERATES_CREDIT = "GENERATES_CREDIT"
    DOES_NOT_GENERATE_CREDIT = "DOES_NOT_GENERATE_CREDIT"


class UnavailabilityEventType(StrEnum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    REACTIVATED = "REACTIVATED"


UNAVAILABILITY_LABELS = {
    UnavailabilityCode.LF.value: "LF",
    UnavailabilityCode.LP.value: "LP",
    UnavailabilityCode.BM.value: "Baixa médica",
    UnavailabilityCode.LC.value: "LC",
    UnavailabilityCode.LN.value: "LN",
    UnavailabilityCode.DIL.value: "Diligência",
    UnavailabilityCode.TRIB.value: "Tribunal",
    UnavailabilityCode.INQ.value: "Inquérito",
    UnavailabilityCode.FORMACAO.value: "Formação",
    UnavailabilityCode.TIRO.value: "Tiro",
    UnavailabilityCode.OUTRA.value: "Outra ausência",
}

ALLOWED_UNAVAILABILITY_CODES = tuple(item.value for item in UnavailabilityCode)
ALLOWED_UNAVAILABILITY_STATUSES = tuple(item.value for item in UnavailabilityStatus)
ALLOWED_COMPENSATION_STATUSES = tuple(item.value for item in CompensationStatus)


class Unavailability(db.Model):
    __tablename__ = "unavailabilities"
    __table_args__ = (
        db.CheckConstraint(
            "code in ('LF', 'LP', 'BM', 'LC', 'LN', 'DIL', 'TRIB', 'INQ', 'FORMACAO', 'TIRO', 'OUTRA')",
            name="ck_unavailabilities_code",
        ),
        db.CheckConstraint(
            "status in ('PLANNED', 'CONFIRMED', 'CANCELLED')",
            name="ck_unavailabilities_status",
        ),
        db.CheckConstraint(
            "compensation_status in ('NOT_APPLICABLE', 'PENDING_DECISION', 'GENERATES_CREDIT', 'DOES_NOT_GENERATE_CREDIT')",
            name="ck_unavailabilities_compensation_status",
        ),
        db.CheckConstraint(
            "end_date >= start_date",
            name="ck_unavailabilities_date_period",
        ),
        db.CheckConstraint(
            "(is_full_day = 1 and start_time is null and end_time is null) or "
            "(is_full_day = 0 and start_time is not null and end_time is not null)",
            name="ck_unavailabilities_time_semantics",
        ),
        db.CheckConstraint(
            "travel_minutes_before >= 0 and travel_minutes_after >= 0",
            name="ck_unavailabilities_travel_non_negative",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    military_id = db.Column(db.Integer, db.ForeignKey("militaries.id"), nullable=False, index=True)
    code = db.Column(db.String(30), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False, index=True)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    is_full_day = db.Column(db.Boolean, nullable=False, default=True)
    status = db.Column(db.String(30), nullable=False, default=UnavailabilityStatus.PLANNED.value, index=True)
    reason = db.Column(db.String(500), nullable=False)
    location = db.Column(db.String(250), nullable=True)
    travel_minutes_before = db.Column(db.Integer, nullable=False, default=0)
    travel_minutes_after = db.Column(db.Integer, nullable=False, default=0)
    compensation_status = db.Column(
        db.String(40),
        nullable=False,
        default=CompensationStatus.NOT_APPLICABLE.value,
        index=True,
    )
    compensation_notes = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    military = db.relationship("Military", back_populates="unavailabilities")
    events = db.relationship(
        "UnavailabilityEvent",
        back_populates="unavailability",
        order_by="UnavailabilityEvent.created_at.asc()",
    )

    @property
    def is_blocking(self) -> bool:
        return self.is_active and self.status == UnavailabilityStatus.CONFIRMED.value

    @property
    def crosses_midnight(self) -> bool:
        return not self.is_full_day and self.end_date == self.start_date and self.end_time <= self.start_time


class UnavailabilityEvent(db.Model):
    __tablename__ = "unavailability_events"
    __table_args__ = (
        db.CheckConstraint(
            "event_type in ('CREATED', 'UPDATED', 'CONFIRMED', 'CANCELLED', 'REACTIVATED')",
            name="ck_unavailability_events_type",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    unavailability_id = db.Column(
        db.Integer,
        db.ForeignKey("unavailabilities.id"),
        nullable=False,
        index=True,
    )
    event_type = db.Column(db.String(30), nullable=False, index=True)
    previous_status = db.Column(db.String(30), nullable=True)
    new_status = db.Column(db.String(30), nullable=True)
    description = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    unavailability = db.relationship("Unavailability", back_populates="events")
