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


class AssignmentSource(StrEnum):
    MANUAL = "MANUAL"
    SYSTEM = "SYSTEM"
    IMPORTED = "IMPORTED"


class AssignmentChangeType(StrEnum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    CLEARED = "CLEARED"
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    OVERRIDE_APPLIED = "OVERRIDE_APPLIED"
    OVERRIDE_REMOVED = "OVERRIDE_REMOVED"


ALLOWED_SCHEDULE_MONTH_STATUSES = tuple(item.value for item in ScheduleMonthStatus)
ALLOWED_SCHEDULE_VERSION_SOURCES = tuple(item.value for item in ScheduleVersionSource)
ALLOWED_ASSIGNMENT_SOURCES = tuple(item.value for item in AssignmentSource)
ALLOWED_ASSIGNMENT_CHANGE_TYPES = tuple(item.value for item in AssignmentChangeType)


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
    assignments = db.relationship(
        "Assignment",
        back_populates="schedule_version",
        order_by="Assignment.assignment_date.asc(), Assignment.id.asc()",
    )


class Assignment(db.Model):
    __tablename__ = "assignments"
    __table_args__ = (
        db.UniqueConstraint(
            "schedule_version_id",
            "military_id",
            "assignment_date",
            name="uq_assignments_version_military_date",
        ),
        db.CheckConstraint(
            "source in ('MANUAL', 'SYSTEM', 'IMPORTED')",
            name="ck_assignments_source",
        ),
        db.CheckConstraint(
            "code is null or length(code) between 1 and 30",
            name="ck_assignments_code_length",
        ),
        db.CheckConstraint(
            "code is null or code in ('AT1', 'AT2', 'AT3', 'PO1', 'PO2', 'PO3', 'PT', 'P', 'R', 'CR', 'FC', 'FF', 'DS', 'DC', 'LF', 'LP', 'BM', 'LC', 'LN', 'DIL', 'TRIB', 'INQ', 'DCP', 'D24', 'FORMACAO', 'TIRO', 'OUTRA')",
            name="ck_assignments_code",
        ),
        db.CheckConstraint(
            "(is_cleared = 1 and code is null) or (is_cleared = 0 and code is not null)",
            name="ck_assignments_cleared_code",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    schedule_version_id = db.Column(
        db.Integer,
        db.ForeignKey("schedule_versions.id"),
        nullable=False,
        index=True,
    )
    military_id = db.Column(
        db.Integer,
        db.ForeignKey("militaries.id"),
        nullable=False,
        index=True,
    )
    assignment_date = db.Column(db.Date, nullable=False, index=True)
    code = db.Column(db.String(30), nullable=True, index=True)
    source = db.Column(
        db.String(30),
        nullable=False,
        default=AssignmentSource.MANUAL.value,
        index=True,
    )
    is_manual = db.Column(db.Boolean, nullable=False, default=True, index=True)
    is_locked = db.Column(db.Boolean, nullable=False, default=True, index=True)
    has_override = db.Column(db.Boolean, nullable=False, default=False, index=True)
    override_reason = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    is_cleared = db.Column(db.Boolean, nullable=False, default=False, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    schedule_version = db.relationship("ScheduleVersion", back_populates="assignments")
    military = db.relationship("Military")
    changes = db.relationship(
        "AssignmentChange",
        back_populates="assignment",
        order_by="AssignmentChange.created_at.asc(), AssignmentChange.id.asc()",
    )

    @property
    def is_visible(self) -> bool:
        return not self.is_cleared and self.code is not None


class AssignmentChange(db.Model):
    __tablename__ = "assignment_changes"
    __table_args__ = (
        db.CheckConstraint(
            "change_type in ('CREATED', 'UPDATED', 'CLEARED', 'LOCKED', 'UNLOCKED', 'OVERRIDE_APPLIED', 'OVERRIDE_REMOVED')",
            name="ck_assignment_changes_type",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(
        db.Integer,
        db.ForeignKey("assignments.id"),
        nullable=False,
        index=True,
    )
    change_type = db.Column(db.String(40), nullable=False, index=True)
    previous_code = db.Column(db.String(30), nullable=True)
    new_code = db.Column(db.String(30), nullable=True)
    previous_locked = db.Column(db.Boolean, nullable=True)
    new_locked = db.Column(db.Boolean, nullable=True)
    previous_override = db.Column(db.Boolean, nullable=True)
    new_override = db.Column(db.Boolean, nullable=True)
    reason = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    assignment = db.relationship("Assignment", back_populates="changes")
