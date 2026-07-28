from dataclasses import dataclass, field
from datetime import date

from app.extensions import db
from app.models import (
    Assignment,
    AssignmentChange,
    AssignmentChangeType,
    AssignmentSource,
    GenerationMode,
    GenerationRun,
    GenerationRunStatus,
    ScheduleMonthStatus,
    ScheduleVersion,
    ScheduleVersionSource,
)
from app.models.military import utc_now
from app.services.diagnostic_service import ScheduleDiagnosticService
from app.services.schedule_generator import (
    GENERATION_SERVICE_CODES,
    PTGenerationOptions,
    ScheduleGenerationError,
    ScheduleGenerator,
    generation_parameters,
)
from app.services.service_code_catalog import COVERAGE_TARGETS


ALLOWED_REGENERATION_SOURCE_STATUSES = {
    ScheduleMonthStatus.DRAFT.value,
    ScheduleMonthStatus.VALIDATED.value,
}


class ScheduleRegenerationError(Exception):
    def __init__(self, message: str, errors: dict[str, str] | None = None):
        super().__init__(message)
        self.errors = errors or {}


@dataclass(frozen=True)
class RegenerationSummary:
    source_version_id: int
    result_version_id: int
    generation_run_id: int
    copied_assignments: int
    skipped_automatic_assignments: int


@dataclass(frozen=True)
class VersionComparison:
    source_version: ScheduleVersion
    result_version: ScheduleVersion
    preserved_manual: int
    removed_automatic: int
    created_automatic: int
    changed_codes: list[dict] = field(default_factory=list)
    changed_militaries: list[dict] = field(default_factory=list)
    source_unfilled: int = 0
    result_unfilled: int = 0

    @property
    def total_differences(self) -> int:
        return (
            self.removed_automatic
            + self.created_automatic
            + len(self.changed_codes)
            + len(self.changed_militaries)
            + abs(self.source_unfilled - self.result_unfilled)
        )


class ScheduleRegenerationService:
    def __init__(self, generator: ScheduleGenerator | None = None):
        self.generator = generator or ScheduleGenerator()

    def regenerate_automatic_at_po(
        self,
        source_version: ScheduleVersion,
        pt_options: PTGenerationOptions | None = None,
    ) -> RegenerationSummary:
        validate_regeneration_source(source_version)
        ensure_no_running_regeneration(source_version.id)
        pt_options = pt_options or PTGenerationOptions()
        pt_options.validate()

        copied_count = 0
        skipped_automatic_count = 0
        try:
            next_number = next_version_number(source_version)
            result_version = ScheduleVersion(
                schedule_month_id=source_version.schedule_month_id,
                version_number=next_number,
                status=ScheduleMonthStatus.DRAFT.value,
                source=ScheduleVersionSource.SYSTEM.value,
                parent_version_id=source_version.id,
                generation_mode=GenerationMode.REGENERATE_AUTOMATIC.value,
                description=f"Regeneracao automatica AT/PO a partir da versao {source_version.version_number}.",
            )
            db.session.add(result_version)
            db.session.flush()

            copied_count, skipped_automatic_count = copy_preserved_assignments(source_version, result_version)
            run = GenerationRun(
                schedule_version_id=result_version.id,
                source_version_id=source_version.id,
                result_version_id=result_version.id,
                generation_mode=GenerationMode.REGENERATE_AUTOMATIC.value,
                parameters_json=regeneration_parameters(source_version, result_version, pt_options),
            )
            db.session.add(run)
            db.session.flush()

            self.generator.generate_into_version(result_version, run, commit=False, pt_options=pt_options)
            db.session.commit()
        except ScheduleGenerationError:
            db.session.rollback()
            raise
        except Exception as exc:
            db.session.rollback()
            raise ScheduleRegenerationError("A regeneracao falhou.", {"regeneration": str(exc)}) from exc

        diagnostic_run = ScheduleDiagnosticService().run_and_persist(result_version)
        run.diagnostic_run_id = diagnostic_run.id
        db.session.commit()
        return RegenerationSummary(
            source_version_id=source_version.id,
            result_version_id=result_version.id,
            generation_run_id=run.id,
            copied_assignments=copied_count,
            skipped_automatic_assignments=skipped_automatic_count,
        )


def validate_regeneration_source(source_version: ScheduleVersion | None) -> None:
    if source_version is None:
        raise ScheduleRegenerationError("Versao inexistente.", {"version": "Versao inexistente."})
    if source_version.status not in ALLOWED_REGENERATION_SOURCE_STATUSES:
        raise ScheduleRegenerationError(
            "Estado da versao nao permite regeneracao.",
            {"status": "Apenas versoes DRAFT ou VALIDATED podem originar nova versao nesta fase."},
        )


def ensure_no_running_regeneration(source_version_id: int) -> None:
    running = GenerationRun.query.filter_by(
        source_version_id=source_version_id,
        generation_mode=GenerationMode.REGENERATE_AUTOMATIC.value,
        status=GenerationRunStatus.RUNNING.value,
    ).first()
    if running is not None:
        raise ScheduleRegenerationError(
            "Ja existe regeneracao em curso.",
            {"running": "Aguarde a conclusao da regeneracao em curso."},
        )


def next_version_number(source_version: ScheduleVersion) -> int:
    current = max((version.version_number for version in source_version.schedule_month.versions), default=0)
    return current + 1


def copy_preserved_assignments(source_version: ScheduleVersion, result_version: ScheduleVersion) -> tuple[int, int]:
    copied_count = 0
    skipped_automatic_count = 0
    for assignment in sorted(source_version.assignments, key=lambda item: (item.assignment_date, item.military_id, item.id)):
        if assignment.source == AssignmentSource.SYSTEM.value:
            if assignment.is_visible:
                skipped_automatic_count += 1
            continue
        if assignment.is_cleared or not assignment.is_visible:
            continue
        if assignment.source not in {AssignmentSource.MANUAL.value, AssignmentSource.IMPORTED.value}:
            continue
        copy = Assignment(
            schedule_version_id=result_version.id,
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
                reason=f"Copiada da versao {source_version.version_number}, atribuicao {assignment.id}.",
            )
        )
        copied_count += 1
    return copied_count, skipped_automatic_count


def regeneration_parameters(source_version: ScheduleVersion, result_version: ScheduleVersion, pt_options: PTGenerationOptions | None = None) -> str:
    params = generation_parameters(pt_options)
    params["mode"] = GenerationMode.REGENERATE_AUTOMATIC.value
    params["source_version_id"] = source_version.id
    params["result_version_id"] = result_version.id
    return __import__("json").dumps(params, sort_keys=True)


def compare_versions(source_version: ScheduleVersion, result_version: ScheduleVersion) -> VersionComparison:
    source_assignments = visible_assignments(source_version)
    result_assignments = visible_assignments(result_version)
    source_by_cell = {(item.assignment_date, item.military_id): item for item in source_assignments}
    result_by_cell = {(item.assignment_date, item.military_id): item for item in result_assignments}

    preserved_manual = sum(
        1
        for source in source_assignments
        if source.source == AssignmentSource.MANUAL.value
        and any(
            result.military_id == source.military_id
            and result.assignment_date == source.assignment_date
            and result.code == source.code
            and result.source == source.source
            for result in result_assignments
        )
    )
    removed_automatic = sum(1 for item in source_assignments if item.source == AssignmentSource.SYSTEM.value)
    created_automatic = sum(1 for item in result_assignments if item.source == AssignmentSource.SYSTEM.value)

    changed_codes = []
    for key, source in source_by_cell.items():
        result = result_by_cell.get(key)
        if result is not None and source.code != result.code:
            changed_codes.append(
                {
                    "date": key[0],
                    "military_id": key[1],
                    "source_code": source.code,
                    "result_code": result.code,
                }
            )

    changed_militaries = []
    for assignment_date, code in sorted({(item.assignment_date, item.code) for item in source_assignments + result_assignments if item.code in GENERATION_SERVICE_CODES}):
        source_ids = sorted(item.military_id for item in source_assignments if item.assignment_date == assignment_date and item.code == code)
        result_ids = sorted(item.military_id for item in result_assignments if item.assignment_date == assignment_date and item.code == code)
        if source_ids != result_ids:
            changed_militaries.append(
                {
                    "date": assignment_date,
                    "code": code,
                    "source_military_ids": source_ids,
                    "result_military_ids": result_ids,
                }
            )

    return VersionComparison(
        source_version=source_version,
        result_version=result_version,
        preserved_manual=preserved_manual,
        removed_automatic=removed_automatic,
        created_automatic=created_automatic,
        changed_codes=changed_codes,
        changed_militaries=changed_militaries,
        source_unfilled=count_unfilled(source_version),
        result_unfilled=count_unfilled(result_version),
    )


def visible_assignments(version: ScheduleVersion) -> list[Assignment]:
    return [assignment for assignment in version.assignments if assignment.is_visible]


def count_unfilled(version: ScheduleVersion) -> int:
    month = version.schedule_month
    current = date(month.year, month.month, 1)
    if month.month == 12:
        next_month = date(month.year + 1, 1, 1)
    else:
        next_month = date(month.year, month.month + 1, 1)
    end = next_month
    total = 0
    assignments = visible_assignments(version)
    while current < end:
        for code, target in COVERAGE_TARGETS.items():
            count = sum(1 for item in assignments if item.assignment_date == current and item.code == code)
            total += max(target - count, 0)
        current = date.fromordinal(current.toordinal() + 1)
    return total
