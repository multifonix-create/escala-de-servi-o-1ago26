from enum import StrEnum

from app.extensions import db
from app.models.military import utc_now


class RestrictionType(StrEnum):
    UNAVAILABLE = "UNAVAILABLE"
    AVAILABLE_ONLY = "AVAILABLE_ONLY"
    SPECIAL_AVAILABILITY = "SPECIAL_AVAILABILITY"


ALLOWED_RESTRICTION_TYPES = tuple(item.value for item in RestrictionType)

WEEKDAY_FIELDS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


class MilitaryRestriction(db.Model):
    __tablename__ = "military_restrictions"
    __table_args__ = (
        db.CheckConstraint(
            "restriction_type in ('UNAVAILABLE', 'AVAILABLE_ONLY', 'SPECIAL_AVAILABILITY')",
            name="ck_military_restrictions_type",
        ),
        db.CheckConstraint(
            "end_date is null or end_date >= start_date",
            name="ck_military_restrictions_date_period",
        ),
        db.CheckConstraint(
            "(start_time is null and end_time is null) or (start_time is not null and end_time is not null)",
            name="ck_military_restrictions_time_pair",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    military_id = db.Column(
        db.Integer,
        db.ForeignKey("militaries.id"),
        nullable=False,
        index=True,
    )
    restriction_type = db.Column(db.String(40), nullable=False, index=True)
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=True, index=True)
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    monday = db.Column(db.Boolean, nullable=False, default=False)
    tuesday = db.Column(db.Boolean, nullable=False, default=False)
    wednesday = db.Column(db.Boolean, nullable=False, default=False)
    thursday = db.Column(db.Boolean, nullable=False, default=False)
    friday = db.Column(db.Boolean, nullable=False, default=False)
    saturday = db.Column(db.Boolean, nullable=False, default=False)
    sunday = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    reason = db.Column(db.String(500), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    military = db.relationship("Military", back_populates="restrictions")

    @property
    def is_full_day(self) -> bool:
        return self.start_time is None and self.end_time is None

    @property
    def crosses_midnight(self) -> bool:
        return (
            self.start_time is not None
            and self.end_time is not None
            and self.end_time <= self.start_time
        )

    @property
    def selected_weekdays(self) -> tuple[str, ...]:
        return tuple(field for field in WEEKDAY_FIELDS if getattr(self, field))

    def applies_to_weekday(self, weekday: int) -> bool:
        selected = self.selected_weekdays
        if not selected:
            return True
        return WEEKDAY_FIELDS[weekday] in selected
