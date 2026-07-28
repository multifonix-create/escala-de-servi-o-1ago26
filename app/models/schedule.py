from enum import StrEnum

from app.extensions import db
from app.models.military import utc_now


class ScheduleMonthStatus(StrEnum):
    NOT_GENERATED = "NOT_GENERATED"
    DRAFT = "DRAFT"
    VALIDATED = "VALIDATED"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"


class ScheduleVersionSource(StrEnum):
    INITIAL = "INITIAL"
    MANUAL = "MANUAL"
    SYSTEM = "SYSTEM"


ALLOWED_SCHEDULE_MONTH_STATUSES = tuple(item.value for item in ScheduleMonthStatus)
ALLOWED_SCHEDULE_VERSION_SOURCES = tuple(item.value for item in ScheduleVersionSource)


class ScheduleMonth(db.Model):
    __tablename__ = "schedule_months"
    __table_args__ = (
        db.UniqueConstraint("year", "month", name="uq_schedule_months_year_month"),
        db.CheckConstraint("month between 1 and 12", name="ck_schedule_months_month"),
        db.CheckConstraint("year between 2000 and 2100", name="ck_schedule_months_year"),
        db.CheckConstraint(
            "status in ('NOT_GENERATED', 'DRAFT', 'VALIDATED', 'PUBLISHED', 'CLOSED')",
            name="ck_schedule_months_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False, index=True)
    month = db.Column(db.Integer, nullable=False, index=True)
    status = db.Column(
        db.String(30),
        nullable=False,
        default=ScheduleMonthStatus.DRAFT.value,
        index=True,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    versions = db.relationship(
        "ScheduleVersion",
        back_populates="schedule_month",
        cascade="all, delete-orphan",
        order_by="ScheduleVersion.version_number.asc()",
    )

    @property
    def label(self) -> str:
        return f"{self.month:02d}/{self.year}"

    @property
    def latest_version(self):
        if not self.versions:
            return None
        return max(self.versions, key=lambda version: version.version_number)


class ScheduleVersion(db.Model):
    __tablename__ = "schedule_versions"
    __table_args__ = (
        db.UniqueConstraint(
            "schedule_month_id",
            "version_number",
            name="uq_schedule_versions_month_number",
        ),
        db.CheckConstraint("version_number >= 1", name="ck_schedule_versions_number"),
        db.CheckConstraint(
            "status in ('NOT_GENERATED', 'DRAFT', 'VALIDATED', 'PUBLISHED', 'CLOSED')",
            name="ck_schedule_versions_status",
        ),
        db.CheckConstraint(
            "source in ('INITIAL', 'MANUAL', 'SYSTEM')",
            name="ck_schedule_versions_source",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    schedule_month_id = db.Column(
        db.Integer,
        db.ForeignKey("schedule_months.id"),
        nullable=False,
        index=True,
    )
    version_number = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.String(30),
        nullable=False,
        default=ScheduleMonthStatus.DRAFT.value,
        index=True,
    )
    source = db.Column(
        db.String(30),
        nullable=False,
        default=ScheduleVersionSource.INITIAL.value,
        index=True,
    )
    description = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    schedule_month = db.relationship("ScheduleMonth", back_populates="versions")
