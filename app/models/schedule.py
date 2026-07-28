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


class DiagnosticLevel(StrEnum):
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"


class DiagnosticCategory(StrEnum):
    CONFIGURATION = "CONFIGURATION"
    MILITARY = "MILITARY"
    TEAM = "TEAM"
    CYCLE = "CYCLE"
    UNAVAILABILITY = "UNAVAILABILITY"
    RESTRICTION = "RESTRICTION"
    ASSIGNMENT = "ASSIGNMENT"
    SCHEDULE_STATE = "SCHEDULE_STATE"
    COVERAGE = "COVERAGE"
    REST = "REST"
    COMPENSATION = "COMPENSATION"
    SYSTEM = "SYSTEM"


class DiagnosticRunStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GenerationRunStatus(StrEnum):
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_WARNINGS = "COMPLETED_WITH_WARNINGS"
    FAILED = "FAILED"


class GenerationMode(StrEnum):
    FILL_EMPTY = "FILL_EMPTY"
    REGENERATE_AUTOMATIC = "REGENERATE_AUTOMATIC"


class ScheduleVersionStateEventType(StrEnum):
    VALIDATED = "VALIDATED"
    VALIDATION_REVOKED = "VALIDATION_REVOKED"
    PUBLISHED = "PUBLISHED"
    UNPUBLISHED = "UNPUBLISHED"
    CLOSED = "CLOSED"
    REOPENED_AS_NEW_VERSION = "REOPENED_AS_NEW_VERSION"


ALLOWED_SCHEDULE_MONTH_STATUSES = tuple(item.value for item in ScheduleMonthStatus)
ALLOWED_SCHEDULE_VERSION_SOURCES = tuple(item.value for item in ScheduleVersionSource)
ALLOWED_ASSIGNMENT_SOURCES = tuple(item.value for item in AssignmentSource)
ALLOWED_ASSIGNMENT_CHANGE_TYPES = tuple(item.value for item in AssignmentChangeType)
ALLOWED_DIAGNOSTIC_LEVELS = tuple(item.value for item in DiagnosticLevel)
ALLOWED_DIAGNOSTIC_CATEGORIES = tuple(item.value for item in DiagnosticCategory)
ALLOWED_DIAGNOSTIC_RUN_STATUSES = tuple(item.value for item in DiagnosticRunStatus)
ALLOWED_GENERATION_RUN_STATUSES = tuple(item.value for item in GenerationRunStatus)
ALLOWED_GENERATION_MODES = tuple(item.value for item in GenerationMode)
ALLOWED_SCHEDULE_VERSION_STATE_EVENT_TYPES = tuple(item.value for item in ScheduleVersionStateEventType)


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
    published_version_id = db.Column(
        db.Integer,
        db.ForeignKey("schedule_versions.id"),
        nullable=True,
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
        foreign_keys="ScheduleVersion.schedule_month_id",
        cascade="all, delete-orphan",
        order_by="ScheduleVersion.version_number.asc()",
    )
    published_version = db.relationship(
        "ScheduleVersion",
        foreign_keys=[published_version_id],
        post_update=True,
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
        db.CheckConstraint(
            "generation_mode is null or generation_mode in ('FILL_EMPTY', 'REGENERATE_AUTOMATIC')",
            name="ck_schedule_versions_generation_mode",
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
    parent_version_id = db.Column(
        db.Integer,
        db.ForeignKey("schedule_versions.id"),
        nullable=True,
        index=True,
    )
    generation_mode = db.Column(db.String(40), nullable=True, index=True)
    description = db.Column(db.String(500), nullable=True)
    content_revision = db.Column(db.Integer, nullable=False, default=0)
    validated_revision = db.Column(db.Integer, nullable=True)
    validated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    validated_diagnostic_run_id = db.Column(
        db.Integer,
        db.ForeignKey("diagnostic_runs.id"),
        nullable=True,
        index=True,
    )
    published_at = db.Column(db.DateTime(timezone=True), nullable=True)
    closed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    state_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    schedule_month = db.relationship(
        "ScheduleMonth",
        back_populates="versions",
        foreign_keys=[schedule_month_id],
    )
    parent_version = db.relationship("ScheduleVersion", remote_side=[id])
    validated_diagnostic_run = db.relationship(
        "DiagnosticRun",
        foreign_keys=[validated_diagnostic_run_id],
    )
    assignments = db.relationship(
        "Assignment",
        back_populates="schedule_version",
        order_by="Assignment.assignment_date.asc(), Assignment.id.asc()",
    )
    state_events = db.relationship(
        "ScheduleVersionStateEvent",
        back_populates="schedule_version",
        order_by="ScheduleVersionStateEvent.created_at.asc(), ScheduleVersionStateEvent.id.asc()",
    )


class ScheduleVersionStateEvent(db.Model):
    __tablename__ = "schedule_version_state_events"
    __table_args__ = (
        db.CheckConstraint(
            "event_type in ('VALIDATED', 'VALIDATION_REVOKED', 'PUBLISHED', 'UNPUBLISHED', 'CLOSED', 'REOPENED_AS_NEW_VERSION')",
            name="ck_schedule_version_state_events_type",
        ),
        db.CheckConstraint(
            "previous_state is null or previous_state in ('NOT_GENERATED', 'DRAFT', 'VALIDATED', 'PUBLISHED', 'CLOSED')",
            name="ck_schedule_version_state_events_previous_state",
        ),
        db.CheckConstraint(
            "new_state is null or new_state in ('NOT_GENERATED', 'DRAFT', 'VALIDATED', 'PUBLISHED', 'CLOSED')",
            name="ck_schedule_version_state_events_new_state",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    schedule_version_id = db.Column(
        db.Integer,
        db.ForeignKey("schedule_versions.id"),
        nullable=False,
        index=True,
    )
    event_type = db.Column(db.String(50), nullable=False, index=True)
    previous_state = db.Column(db.String(30), nullable=True)
    new_state = db.Column(db.String(30), nullable=True)
    reason = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    diagnostic_run_id = db.Column(
        db.Integer,
        db.ForeignKey("diagnostic_runs.id"),
        nullable=True,
        index=True,
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    schedule_version = db.relationship("ScheduleVersion", back_populates="state_events")
    diagnostic_run = db.relationship("DiagnosticRun")


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
    start_time = db.Column(db.Time, nullable=True)
    end_time = db.Column(db.Time, nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)
    holiday_leave_credit_id = db.Column(
        db.Integer,
        db.ForeignKey("holiday_leave_credits.id"),
        nullable=True,
        index=True,
    )
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
    holiday_leave_credit = db.relationship(
        "HolidayLeaveCredit",
        foreign_keys=[holiday_leave_credit_id],
    )
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


class DiagnosticRun(db.Model):
    __tablename__ = "diagnostic_runs"
    __table_args__ = (
        db.CheckConstraint(
            "status in ('RUNNING', 'COMPLETED', 'FAILED')",
            name="ck_diagnostic_runs_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    schedule_version_id = db.Column(
        db.Integer,
        db.ForeignKey("schedule_versions.id"),
        nullable=False,
        index=True,
    )
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    status = db.Column(
        db.String(30),
        nullable=False,
        default=DiagnosticRunStatus.RUNNING.value,
        index=True,
    )
    total_errors = db.Column(db.Integer, nullable=False, default=0)
    total_warnings = db.Column(db.Integer, nullable=False, default=0)
    total_infos = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    schedule_version = db.relationship("ScheduleVersion", foreign_keys=[schedule_version_id])
    issues = db.relationship(
        "DiagnosticIssue",
        back_populates="diagnostic_run",
        order_by="DiagnosticIssue.level.asc(), DiagnosticIssue.category.asc(), DiagnosticIssue.code.asc(), DiagnosticIssue.id.asc()",
    )


class DiagnosticIssue(db.Model):
    __tablename__ = "diagnostic_issues"
    __table_args__ = (
        db.CheckConstraint(
            "level in ('ERROR', 'WARNING', 'INFO')",
            name="ck_diagnostic_issues_level",
        ),
        db.CheckConstraint(
            "category in ('CONFIGURATION', 'MILITARY', 'TEAM', 'CYCLE', 'UNAVAILABILITY', 'RESTRICTION', 'ASSIGNMENT', 'SCHEDULE_STATE', 'COVERAGE', 'REST', 'COMPENSATION', 'SYSTEM')",
            name="ck_diagnostic_issues_category",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    diagnostic_run_id = db.Column(
        db.Integer,
        db.ForeignKey("diagnostic_runs.id"),
        nullable=False,
        index=True,
    )
    level = db.Column(db.String(20), nullable=False, index=True)
    category = db.Column(db.String(40), nullable=False, index=True)
    code = db.Column(db.String(80), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    assignment_date = db.Column(db.Date, nullable=True, index=True)
    military_id = db.Column(db.Integer, db.ForeignKey("militaries.id"), nullable=True, index=True)
    team_id = db.Column(db.Integer, db.ForeignKey("teams.id"), nullable=True, index=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey("assignments.id"), nullable=True, index=True)
    is_blocking = db.Column(db.Boolean, nullable=False, default=False, index=True)
    suggested_action = db.Column(db.Text, nullable=True)
    details_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    diagnostic_run = db.relationship("DiagnosticRun", back_populates="issues")
    military = db.relationship("Military")
    team = db.relationship("Team")
    assignment = db.relationship("Assignment")


class GenerationRun(db.Model):
    __tablename__ = "generation_runs"
    __table_args__ = (
        db.CheckConstraint(
            "status in ('RUNNING', 'COMPLETED', 'COMPLETED_WITH_WARNINGS', 'FAILED')",
            name="ck_generation_runs_status",
        ),
        db.CheckConstraint(
            "generation_mode is null or generation_mode in ('FILL_EMPTY', 'REGENERATE_AUTOMATIC')",
            name="ck_generation_runs_generation_mode",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    schedule_version_id = db.Column(
        db.Integer,
        db.ForeignKey("schedule_versions.id"),
        nullable=False,
        index=True,
    )
    diagnostic_run_id = db.Column(
        db.Integer,
        db.ForeignKey("diagnostic_runs.id"),
        nullable=True,
        index=True,
    )
    source_version_id = db.Column(
        db.Integer,
        db.ForeignKey("schedule_versions.id"),
        nullable=True,
        index=True,
    )
    result_version_id = db.Column(
        db.Integer,
        db.ForeignKey("schedule_versions.id"),
        nullable=True,
        index=True,
    )
    generation_mode = db.Column(db.String(40), nullable=True, index=True)
    status = db.Column(
        db.String(40),
        nullable=False,
        default=GenerationRunStatus.RUNNING.value,
        index=True,
    )
    started_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    total_created = db.Column(db.Integer, nullable=False, default=0)
    total_preserved_manual = db.Column(db.Integer, nullable=False, default=0)
    total_unfilled = db.Column(db.Integer, nullable=False, default=0)
    total_warnings = db.Column(db.Integer, nullable=False, default=0)
    parameters_json = db.Column(db.Text, nullable=True)
    summary_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    schedule_version = db.relationship("ScheduleVersion", foreign_keys=[schedule_version_id])
    source_version = db.relationship("ScheduleVersion", foreign_keys=[source_version_id])
    result_version = db.relationship("ScheduleVersion", foreign_keys=[result_version_id])
    diagnostic_run = db.relationship("DiagnosticRun")
    selection_details = db.relationship(
        "AssignmentSelectionDetail",
        back_populates="generation_run",
        order_by="AssignmentSelectionDetail.assignment_date.asc(), AssignmentSelectionDetail.service_code.asc(), AssignmentSelectionDetail.position.asc(), AssignmentSelectionDetail.id.asc()",
    )


class AssignmentSelectionDetail(db.Model):
    __tablename__ = "assignment_selection_details"
    __table_args__ = (
        db.CheckConstraint(
            "service_code in ('AT1', 'AT2', 'AT3', 'PO1', 'PO2', 'PO3', 'PT')",
            name="ck_assignment_selection_details_service_code",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    generation_run_id = db.Column(
        db.Integer,
        db.ForeignKey("generation_runs.id"),
        nullable=False,
        index=True,
    )
    assignment_date = db.Column(db.Date, nullable=False, index=True)
    service_code = db.Column(db.String(30), nullable=False, index=True)
    military_id = db.Column(db.Integer, db.ForeignKey("militaries.id"), nullable=True, index=True)
    is_eligible = db.Column(db.Boolean, nullable=False, default=False, index=True)
    is_selected = db.Column(db.Boolean, nullable=False, default=False, index=True)
    reason = db.Column(db.Text, nullable=False)
    position = db.Column(db.Integer, nullable=True)
    metrics_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    generation_run = db.relationship("GenerationRun", back_populates="selection_details")
    military = db.relationship("Military")
