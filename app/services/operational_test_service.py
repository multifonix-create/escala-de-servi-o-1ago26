from dataclasses import dataclass
from datetime import date

from app.extensions import db
from app.models import (
    Assignment,
    DiagnosticIssue,
    DiagnosticLevel,
    OperationalTestDecision,
    OperationalTestEvaluation,
    OperationalTestEvaluationEvent,
    ScheduleMonth,
    ScheduleMonthStatus,
    ScheduleVersion,
    ScheduleVersionSource,
)
from app.models.military import utc_now
from app.services.diagnostic_service import latest_run
from app.services.schedule_service import create_schedule_month, get_schedule_month
from app.services.schedule_version_policy import ScheduleVersionPolicy
from app.services.service_code_catalog import COVERAGE_TARGETS


class OperationalTestError(Exception):
    def __init__(self, message: str, errors: dict[str, str] | None = None):
        super().__init__(message)
        self.errors = errors or {}


@dataclass(frozen=True)
class OperationalTestMetrics:
    manual_changes_count: int
    coverage_missing_count: int
    blocking_errors_count: int
    warnings_count: int


def create_operational_test_version(year: int, month: int, notes: str | None = None) -> ScheduleVersion:
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        schedule_month = create_schedule_month(year, month)

    existing_initial = schedule_month.latest_version
    if existing_initial and not existing_initial.assignments and not existing_initial.is_operational_test:
        version = existing_initial
    else:
        next_number = max((item.version_number for item in schedule_month.versions), default=0) + 1
        version = ScheduleVersion(
            schedule_month_id=schedule_month.id,
            version_number=next_number,
            status=ScheduleMonthStatus.DRAFT.value,
            source=ScheduleVersionSource.MANUAL.value,
            description="Teste operacional criado para afericao local.",
        )
        db.session.add(version)

    version.is_operational_test = True
    version.test_created_at = version.test_created_at or utc_now()
    version.test_notes = _optional_text(notes)
    version.description = "Teste operacional - nao publicar."
    db.session.commit()
    return version


def archive_operational_test(version: ScheduleVersion, reason: str | None) -> ScheduleVersion:
    reason = _required_text(reason, "Indique o motivo do arquivo do teste operacional.")
    policy = ScheduleVersionPolicy(version)
    if not policy.can_archive_operational_test():
        raise OperationalTestError(
            "Teste operacional nao arquivavel.",
            {"status": "Apenas testes operacionais nao publicados e nao arquivados podem ser arquivados."},
        )
    version.is_archived = True
    version.archived_at = utc_now()
    version.archive_reason = reason
    db.session.commit()
    return version


def evaluate_operational_test(
    version: ScheduleVersion,
    decision: str,
    notes: str | None = None,
) -> OperationalTestEvaluation:
    if not ScheduleVersionPolicy(version).can_evaluate_operational_test():
        raise OperationalTestError(
            "Teste operacional nao avaliavel.",
            {"version": "A avaliacao exige uma versao de teste operacional nao arquivada."},
        )
    if decision not in {item.value for item in OperationalTestDecision}:
        raise OperationalTestError("Decisao invalida.", {"decision": "Selecione uma decisao valida."})

    metrics = calculate_operational_test_metrics(version)
    evaluation = version.operational_evaluation
    previous_decision = evaluation.decision if evaluation else None
    if evaluation is None:
        evaluation = OperationalTestEvaluation(schedule_version_id=version.id, decision=decision)
        db.session.add(evaluation)
    evaluation.decision = decision
    evaluation.notes = _optional_text(notes)
    evaluation.manual_changes_count = metrics.manual_changes_count
    evaluation.coverage_missing_count = metrics.coverage_missing_count
    evaluation.blocking_errors_count = metrics.blocking_errors_count
    evaluation.warnings_count = metrics.warnings_count
    db.session.flush()
    db.session.add(
        OperationalTestEvaluationEvent(
            evaluation_id=evaluation.id,
            previous_decision=previous_decision,
            new_decision=decision,
            notes=_optional_text(notes),
        )
    )
    db.session.commit()
    return evaluation


def calculate_operational_test_metrics(version: ScheduleVersion) -> OperationalTestMetrics:
    diagnostic_run = latest_run(version.id)
    assignments = Assignment.query.filter_by(schedule_version_id=version.id, is_cleared=False).all()
    manual_changes_count = sum(1 for assignment in assignments if assignment.is_manual)
    coverage_missing_count = _coverage_missing_count(version, assignments)
    blocking_errors_count = 0
    warnings_count = 0
    if diagnostic_run:
        blocking_errors_count = DiagnosticIssue.query.filter_by(
            diagnostic_run_id=diagnostic_run.id,
            level=DiagnosticLevel.ERROR.value,
            is_blocking=True,
        ).count()
        warnings_count = DiagnosticIssue.query.filter_by(
            diagnostic_run_id=diagnostic_run.id,
            level=DiagnosticLevel.WARNING.value,
        ).count()
    return OperationalTestMetrics(
        manual_changes_count=manual_changes_count,
        coverage_missing_count=coverage_missing_count,
        blocking_errors_count=blocking_errors_count,
        warnings_count=warnings_count,
    )


def _coverage_missing_count(version: ScheduleVersion, assignments: list[Assignment]) -> int:
    schedule_month: ScheduleMonth = version.schedule_month
    current = date(schedule_month.year, schedule_month.month, 1)
    end = date(schedule_month.year, schedule_month.month + 1, 1) if schedule_month.month < 12 else date(schedule_month.year + 1, 1, 1)
    missing = 0
    while current < end:
        for code, target in COVERAGE_TARGETS.items():
            count = sum(1 for assignment in assignments if assignment.assignment_date == current and assignment.code == code)
            if count < target:
                missing += target - count
        current = date.fromordinal(current.toordinal() + 1)
    return missing


def _required_text(value: str | None, message: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise OperationalTestError("Campo obrigatorio.", {"reason": message})
    return normalized


def _optional_text(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None
