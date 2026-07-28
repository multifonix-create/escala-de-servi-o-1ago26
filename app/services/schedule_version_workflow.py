from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date

from app.extensions import db
from app.models import (
    Assignment,
    AssignmentChange,
    AssignmentChangeType,
    DiagnosticIssue,
    DiagnosticLevel,
    DiagnosticRun,
    ScheduleMonthStatus,
    ScheduleVersion,
    ScheduleVersionSource,
    ScheduleVersionStateEvent,
    ScheduleVersionStateEventType,
)
from app.models.military import utc_now
from app.services.diagnostic_service import ScheduleDiagnosticService
from app.services.schedule_version_policy import ScheduleVersionPolicy
from app.services.service_code_catalog import COVERAGE_TARGETS


BLOCKING_VALIDATION_CODES = {
    "ASSIGNMENT-INVALID-CODE",
    "ASSIGNMENT-OUTSIDE-MONTH",
    "ASSIGNMENT-OUTSIDE-MILITARY-PERIOD",
    "CONFIG-MISSING-CYCLE-REFERENCE",
    "COVERAGE-MISSING",
    "FF-CELL-WITHOUT-CREDIT",
    "FF-SCHEDULED-WITHOUT-CELL",
    "FC-CELL-WITHOUT-CREDIT",
    "FC-SCHEDULED-WITHOUT-CELL",
    "FR-CELL-WITHOUT-CREDIT",
    "FR-SCHEDULED-WITHOUT-CELL",
    "PT-AUTO-CONFIRMED-UNAVAILABILITY",
    "PT-AUTO-IN-DS-DC",
    "PT-AUTO-REST-TOO-SHORT",
    "PT-CMD",
    "PT-INVALID-INTERVAL",
    "REST-TOO-SHORT",
    "UNAV-BM-CONFLICT",
    "UNAV-CONFIRMED-CONFLICT",
}


@dataclass
class ScheduleWorkflowError(Exception):
    message: str
    errors: dict[str, str] = field(default_factory=dict)
    diagnostic_run: DiagnosticRun | None = None
    blockers: list[DiagnosticIssue] = field(default_factory=list)
    warnings: list[DiagnosticIssue] = field(default_factory=list)

    def __post_init__(self):
        super().__init__(self.message)


def touch_version_content(schedule_version: ScheduleVersion) -> None:
    schedule_version.content_revision = (schedule_version.content_revision or 0) + 1


class ScheduleVersionWorkflow:
    def __init__(self, diagnostic_service: ScheduleDiagnosticService | None = None):
        self.diagnostic_service = diagnostic_service or ScheduleDiagnosticService()

    def validate_version(
        self,
        version: ScheduleVersion,
        confirm_warnings: bool = False,
        notes: str | None = None,
    ) -> DiagnosticRun:
        if not ScheduleVersionPolicy(version).can_validate():
            raise ScheduleWorkflowError("Estado invalido.", {"status": "Apenas versoes DRAFT podem ser validadas."})

        diagnostic_run = self.diagnostic_service.run_and_persist(version)
        blockers = validation_blockers(version, diagnostic_run)
        warnings = validation_warnings(diagnostic_run)
        if blockers:
            raise ScheduleWorkflowError(
                "A validacao encontrou erros bloqueantes.",
                {"blockers": "Corrija todos os erros bloqueantes antes de validar."},
                diagnostic_run=diagnostic_run,
                blockers=blockers,
                warnings=warnings,
            )
        if warnings and not confirm_warnings:
            raise ScheduleWorkflowError(
                "A validacao encontrou avisos.",
                {"warnings": f"Confirme explicitamente os {len(warnings)} avisos antes de validar."},
                diagnostic_run=diagnostic_run,
                warnings=warnings,
            )

        previous_state = version.status
        version.status = ScheduleMonthStatus.VALIDATED.value
        version.validated_at = utc_now()
        version.validated_revision = version.content_revision or 0
        version.validated_diagnostic_run_id = diagnostic_run.id
        version.state_notes = _optional_text(notes)
        _add_state_event(
            version,
            ScheduleVersionStateEventType.VALIDATED.value,
            previous_state,
            version.status,
            "Validacao da escala.",
            notes,
            diagnostic_run.id,
        )
        db.session.commit()
        return diagnostic_run

    def revoke_validation(self, version: ScheduleVersion, reason: str | None, notes: str | None = None) -> None:
        reason = _required_text(reason, "Indique o motivo da revogacao da validacao.")
        if not ScheduleVersionPolicy(version).can_revoke_validation():
            raise ScheduleWorkflowError("Estado invalido.", {"status": "Apenas versoes VALIDATED podem voltar a DRAFT."})
        previous_state = version.status
        version.status = ScheduleMonthStatus.DRAFT.value
        version.validated_at = None
        version.validated_revision = None
        version.validated_diagnostic_run_id = None
        version.state_notes = _optional_text(notes)
        _add_state_event(
            version,
            ScheduleVersionStateEventType.VALIDATION_REVOKED.value,
            previous_state,
            version.status,
            reason,
            notes,
            None,
        )
        db.session.commit()

    def publish_version(
        self,
        version: ScheduleVersion,
        confirm_replace: bool = False,
        notes: str | None = None,
    ) -> None:
        if version.is_operational_test:
            raise ScheduleWorkflowError(
                "Teste operacional nao publicavel.",
                {"status": "Versoes marcadas como TESTE OPERACIONAL - NAO PUBLICAR nao podem ser publicadas."},
            )
        if not ScheduleVersionPolicy(version).can_publish():
            raise ScheduleWorkflowError("Estado invalido.", {"status": "Apenas versoes VALIDATED podem ser publicadas."})
        if version.validated_diagnostic_run_id is None:
            raise ScheduleWorkflowError("Validacao incompleta.", {"diagnostic": "A versao nao possui diagnostico associado a validacao."})
        if version.validated_revision != (version.content_revision or 0):
            raise ScheduleWorkflowError(
                "A versao foi alterada depois da validacao.",
                {"revision": "Revalide a versao antes de publicar."},
            )

        current_published = current_published_version(version)
        if current_published is not None and current_published.id != version.id and not confirm_replace:
            raise ScheduleWorkflowError(
                "Ja existe uma versao publicada para este mes.",
                {"published": "Confirme explicitamente a substituicao da versao publicada."},
            )

        now = utc_now()
        if current_published is not None and current_published.id != version.id:
            previous_state = current_published.status
            current_published.status = ScheduleMonthStatus.VALIDATED.value
            current_published.published_at = None
            _add_state_event(
                current_published,
                ScheduleVersionStateEventType.UNPUBLISHED.value,
                previous_state,
                current_published.status,
                f"Substituida pela versao {version.version_number}.",
                notes,
                None,
            )

        previous_state = version.status
        version.status = ScheduleMonthStatus.PUBLISHED.value
        version.published_at = now
        version.state_notes = _optional_text(notes)
        version.schedule_month.status = ScheduleMonthStatus.PUBLISHED.value
        version.schedule_month.published_version_id = version.id
        _add_state_event(
            version,
            ScheduleVersionStateEventType.PUBLISHED.value,
            previous_state,
            version.status,
            "Publicacao da escala.",
            notes,
            version.validated_diagnostic_run_id,
        )
        db.session.commit()

    def close_version(
        self,
        version: ScheduleVersion,
        confirm_early: bool = False,
        reason: str | None = None,
        notes: str | None = None,
        today: date | None = None,
    ) -> DiagnosticRun:
        if not ScheduleVersionPolicy(version).can_close():
            raise ScheduleWorkflowError("Estado invalido.", {"status": "Apenas versoes PUBLISHED podem ser encerradas."})
        today = today or date.today()
        month_end = _month_end(version)
        if today <= month_end and not confirm_early:
            raise ScheduleWorkflowError(
                "Encerramento antecipado exige confirmacao.",
                {"early_close": "Confirme explicitamente e indique o motivo para encerrar antes do fim do mes."},
            )
        if today <= month_end:
            reason = _required_text(reason, "Indique o motivo do encerramento antecipado.")

        diagnostic_run = self.diagnostic_service.run_and_persist(version)
        blockers = validation_blockers(version, diagnostic_run)
        if blockers:
            raise ScheduleWorkflowError(
                "O diagnostico final encontrou erros bloqueantes.",
                {"blockers": "Corrija os erros antes de encerrar."},
                diagnostic_run=diagnostic_run,
                blockers=blockers,
                warnings=validation_warnings(diagnostic_run),
            )

        previous_state = version.status
        version.status = ScheduleMonthStatus.CLOSED.value
        version.closed_at = utc_now()
        version.state_notes = _optional_text(notes)
        version.schedule_month.status = ScheduleMonthStatus.CLOSED.value
        _add_state_event(
            version,
            ScheduleVersionStateEventType.CLOSED.value,
            previous_state,
            version.status,
            reason or "Encerramento da escala.",
            notes,
            diagnostic_run.id,
        )
        db.session.commit()
        return diagnostic_run

    def create_correction_version(self, source_version: ScheduleVersion, reason: str | None, notes: str | None = None) -> ScheduleVersion:
        reason = _required_text(reason, "Indique o motivo da versao de correcao.")
        if not ScheduleVersionPolicy(source_version).can_create_correction():
            raise ScheduleWorkflowError("Estado invalido.", {"status": "Apenas versoes CLOSED podem originar correcao."})
        next_number = max((item.version_number for item in source_version.schedule_month.versions), default=0) + 1
        correction = ScheduleVersion(
            schedule_month_id=source_version.schedule_month_id,
            version_number=next_number,
            status=ScheduleMonthStatus.DRAFT.value,
            source=ScheduleVersionSource.MANUAL.value,
            parent_version_id=source_version.id,
            description=f"Versao de correcao da versao {source_version.version_number}.",
            state_notes=_optional_text(notes),
        )
        db.session.add(correction)
        db.session.flush()
        copied = _copy_visible_assignments(source_version, correction)
        if copied:
            touch_version_content(correction)
        _add_state_event(
            source_version,
            ScheduleVersionStateEventType.REOPENED_AS_NEW_VERSION.value,
            source_version.status,
            source_version.status,
            reason,
            notes,
            None,
        )
        db.session.commit()
        return correction


def validation_blockers(version: ScheduleVersion, diagnostic_run: DiagnosticRun) -> list[DiagnosticIssue]:
    issues = [
        issue
        for issue in diagnostic_run.issues
        if issue.is_blocking or issue.code in BLOCKING_VALIDATION_CODES
    ]
    issues.extend(_coverage_blockers(version, diagnostic_run.id))
    seen = set()
    unique = []
    for issue in issues:
        key = (issue.code, issue.assignment_date, issue.military_id, issue.assignment_id)
        if key not in seen:
            unique.append(issue)
            seen.add(key)
    return unique


def validation_warnings(diagnostic_run: DiagnosticRun) -> list[DiagnosticIssue]:
    return [issue for issue in diagnostic_run.issues if issue.level == DiagnosticLevel.WARNING.value]


def current_published_version(version: ScheduleVersion) -> ScheduleVersion | None:
    return (
        ScheduleVersion.query.filter(
            ScheduleVersion.schedule_month_id == version.schedule_month_id,
            ScheduleVersion.status == ScheduleMonthStatus.PUBLISHED.value,
        )
        .order_by(ScheduleVersion.published_at.desc(), ScheduleVersion.id.desc())
        .first()
    )


def _coverage_blockers(version: ScheduleVersion, diagnostic_run_id: int) -> list[DiagnosticIssue]:
    month = version.schedule_month
    current = date(month.year, month.month, 1)
    last = _month_end(version)
    assignments = Assignment.query.filter_by(schedule_version_id=version.id, is_cleared=False).all()
    blockers = []
    while current <= last:
        for code, target in COVERAGE_TARGETS.items():
            count = sum(1 for assignment in assignments if assignment.assignment_date == current and assignment.code == code)
            if count < target:
                blockers.append(
                    DiagnosticIssue(
                        diagnostic_run_id=diagnostic_run_id,
                        level=DiagnosticLevel.ERROR.value,
                        category="COVERAGE",
                        code="COVERAGE-MISSING",
                        title="Cobertura AT/PO incompleta",
                        description=f"{code}: {count}/{target}.",
                        assignment_date=current,
                        is_blocking=True,
                    )
                )
        current = date.fromordinal(current.toordinal() + 1)
    return blockers


def _copy_visible_assignments(source_version: ScheduleVersion, correction: ScheduleVersion) -> int:
    copied = 0
    for assignment in sorted(source_version.assignments, key=lambda item: (item.assignment_date, item.military_id, item.id)):
        if not assignment.is_visible:
            continue
        copy = Assignment(
            schedule_version_id=correction.id,
            military_id=assignment.military_id,
            assignment_date=assignment.assignment_date,
            code=assignment.code,
            source=assignment.source,
            is_manual=assignment.is_manual,
            is_locked=assignment.is_locked,
            has_override=assignment.has_override,
            override_reason=assignment.override_reason,
            notes=assignment.notes,
            start_time=assignment.start_time,
            end_time=assignment.end_time,
            duration_minutes=assignment.duration_minutes,
            holiday_leave_credit_id=assignment.holiday_leave_credit_id,
            compensatory_leave_credit_id=assignment.compensatory_leave_credit_id,
            rescheduled_rest_credit_id=assignment.rescheduled_rest_credit_id,
            is_cleared=False,
        )
        db.session.add(copy)
        db.session.flush()
        db.session.add(
            AssignmentChange(
                assignment=copy,
                change_type=AssignmentChangeType.CREATED.value,
                previous_code=None,
                new_code=copy.code,
                previous_locked=None,
                new_locked=copy.is_locked,
                previous_override=None,
                new_override=copy.has_override,
                reason=f"Copiada da versao fechada {source_version.version_number}, atribuicao {assignment.id}.",
            )
        )
        copied += 1
    return copied


def _add_state_event(
    version: ScheduleVersion,
    event_type: str,
    previous_state: str | None,
    new_state: str | None,
    reason: str | None,
    notes: str | None,
    diagnostic_run_id: int | None,
) -> None:
    db.session.add(
        ScheduleVersionStateEvent(
            schedule_version=version,
            event_type=event_type,
            previous_state=previous_state,
            new_state=new_state,
            reason=_optional_text(reason),
            notes=_optional_text(notes),
            diagnostic_run_id=diagnostic_run_id,
        )
    )


def _month_end(version: ScheduleVersion) -> date:
    month = version.schedule_month
    return date(month.year, month.month, monthrange(month.year, month.month)[1])


def _required_text(value: str | None, message: str) -> str:
    normalized = (value or "").strip()
    if not normalized:
        raise ScheduleWorkflowError("Campo obrigatorio.", {"reason": message})
    return normalized


def _optional_text(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None
