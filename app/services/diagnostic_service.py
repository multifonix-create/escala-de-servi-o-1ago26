import json
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy import or_

from app.extensions import db
from app.models import (
    Assignment,
    AssignmentChange,
    CompensationStatus,
    DiagnosticCategory,
    DiagnosticIssue,
    DiagnosticLevel,
    DiagnosticRun,
    DiagnosticRunStatus,
    FunctionalType,
    GenerationRun,
    GenerationRunStatus,
    Military,
    MilitaryRestriction,
    MilitaryTeamHistory,
    ScheduleMonth,
    ScheduleMonthStatus,
    ScheduleVersion,
    Team,
    TeamCycleReference,
    Unavailability,
    UnavailabilityStatus,
)
from app.models.military import utc_now
from app.services import cycle_calculator, membership_service, restriction_service
from app.services.assignment_codes import ALLOWED_ASSIGNMENT_CODES, OPERATIONAL_ASSIGNMENT_CODES, UNAVAILABILITY_ASSIGNMENT_CODES
from app.services.service_code_catalog import COVERAGE_TARGETS, SERVICE_TIME_WINDOWS
from app.services.unavailability_evaluator import interval_for_unavailability


DIAG_CODES = {
    "MONTH_WITHOUT_VERSION": "CONFIG-MONTH-WITHOUT-VERSION",
    "MILITARY_WITHOUT_TEAM": "MILITARY-WITHOUT-TEAM",
    "TEAM_MISSING_REFERENCE": "CONFIG-MISSING-CYCLE-REFERENCE",
    "CYCLE_MANUAL_MISMATCH": "CYCLE-MANUAL-MISMATCH",
    "CYCLE_MANUAL_REST_DAY": "CYCLE-MANUAL-REST-DAY",
    "UNAV_CONFIRMED_CONFLICT": "UNAV-CONFIRMED-CONFLICT",
    "UNAV_PLANNED_ASSIGNMENT": "UNAV-PLANNED-ASSIGNMENT",
    "UNAV_BM_CONFLICT": "UNAV-BM-CONFLICT",
    "RESTRICTION_CONFLICT": "RESTR-ASSIGNMENT-CONFLICT",
    "ASSIGNMENT_INVALID_CODE": "ASSIGNMENT-INVALID-CODE",
    "ASSIGNMENT_OUTSIDE_MONTH": "ASSIGNMENT-OUTSIDE-MONTH",
    "ASSIGNMENT_OUTSIDE_MILITARY_PERIOD": "ASSIGNMENT-OUTSIDE-MILITARY-PERIOD",
    "ASSIGNMENT_LOCKED": "ASSIGNMENT-LOCKED",
    "ASSIGNMENT_UNLOCKED": "ASSIGNMENT-UNLOCKED",
    "ASSIGNMENT_OVERRIDE": "ASSIGNMENT-OVERRIDE",
    "ASSIGNMENT_OVERRIDE_WITHOUT_REASON": "ASSIGNMENT-OVERRIDE-WITHOUT-REASON",
    "ASSIGNMENT_MISSING_HISTORY": "ASSIGNMENT-MISSING-HISTORY",
    "ASSIGNMENT_FF_FC": "ASSIGNMENT-COMPENSATION-CODE",
    "ASSIGNMENT_R_CR": "ASSIGNMENT-PENDING-SPECIAL-CODE",
    "ASSIGNMENT_UNAV_CODE_WITHOUT_RECORD": "ASSIGNMENT-UNAVAILABILITY-CODE-WITHOUT-RECORD",
    "STATE_DRAFT": "STATE-DRAFT-EDITABLE",
    "STATE_NOT_EDITABLE": "STATE-NOT-EDITABLE",
    "STATE_NOT_GENERATED_WITH_VERSION": "STATE-NOT-GENERATED-WITH-VERSION",
    "COVERAGE_PARTIAL": "COVERAGE-PARTIAL-MANUAL",
    "COVERAGE_COMPLETE": "COVERAGE-COMPLETE",
    "COVERAGE_MISSING": "COVERAGE-MISSING",
    "COVERAGE_EXCESS": "COVERAGE-EXCESS",
    "REST_TOO_SHORT": "REST-TOO-SHORT",
    "REST_NOT_YET_VALIDATED": "REST-NOT-YET-VALIDATED",
    "SYSTEM_EMPTY_ASSIGNMENTS": "SYSTEM-MONTH-WITHOUT-ASSIGNMENTS",
}


@dataclass(frozen=True)
class DiagnosticProblem:
    level: str
    category: str
    code: str
    title: str
    description: str
    assignment_date: date | None = None
    military_id: int | None = None
    team_id: int | None = None
    assignment_id: int | None = None
    is_blocking: bool = False
    suggested_action: str | None = None
    details: dict = field(default_factory=dict)
    detected_at: datetime = field(default_factory=utc_now)

    @property
    def identity(self) -> tuple:
        return (
            self.level,
            self.category,
            self.code,
            self.assignment_date,
            self.military_id,
            self.team_id,
            self.assignment_id,
        )


@dataclass(frozen=True)
class DiagnosticSummary:
    total_errors: int
    total_warnings: int
    total_infos: int
    has_blocking_errors: bool
    affected_categories: list[str]


@dataclass(frozen=True)
class DiagnosticContext:
    schedule_month: ScheduleMonth
    schedule_version: ScheduleVersion
    month_start: date
    month_end: date
    militaries: list[Military]
    assignments: list[Assignment]
    teams: list[Team]
    team_references: list[TeamCycleReference]
    unavailabilities: list[Unavailability]
    restrictions: list[MilitaryRestriction]


class ScheduleDiagnosticService:
    def __init__(self, validators: list | None = None):
        self.validators = validators or [
            ConfigurationDiagnosticValidator(),
            MilitaryDiagnosticValidator(),
            CycleDiagnosticValidator(),
            UnavailabilityDiagnosticValidator(),
            RestrictionDiagnosticValidator(),
            AssignmentDiagnosticValidator(),
            ScheduleStateDiagnosticValidator(),
            CoverageDiagnosticValidator(),
            RestDiagnosticValidator(),
        ]

    def analyze(self, schedule_version: ScheduleVersion) -> tuple[list[DiagnosticProblem], DiagnosticSummary]:
        context = build_context(schedule_version)
        problems = []
        for validator in self.validators:
            problems.extend(validator.validate(context))
        problems = deduplicate(problems)
        problems.sort(key=problem_sort_key)
        return problems, summarize(problems)

    def run_and_persist(self, schedule_version: ScheduleVersion) -> DiagnosticRun:
        diagnostic_run = DiagnosticRun(schedule_version_id=schedule_version.id)
        db.session.add(diagnostic_run)
        db.session.flush()
        try:
            problems, summary = self.analyze(schedule_version)
            for problem in problems:
                db.session.add(issue_from_problem(diagnostic_run, problem))
            diagnostic_run.status = DiagnosticRunStatus.COMPLETED.value
            diagnostic_run.completed_at = utc_now()
            diagnostic_run.total_errors = summary.total_errors
            diagnostic_run.total_warnings = summary.total_warnings
            diagnostic_run.total_infos = summary.total_infos
            db.session.commit()
        except Exception:
            diagnostic_run.status = DiagnosticRunStatus.FAILED.value
            diagnostic_run.completed_at = utc_now()
            db.session.commit()
            raise
        return diagnostic_run


def build_context(schedule_version: ScheduleVersion) -> DiagnosticContext:
    schedule_month = schedule_version.schedule_month
    last_day = monthrange(schedule_month.year, schedule_month.month)[1]
    month_start = date(schedule_month.year, schedule_month.month, 1)
    month_end = date(schedule_month.year, schedule_month.month, last_day)
    militaries = (
        Military.query.filter(
            Military.start_date <= month_end,
            or_(Military.end_date.is_(None), Military.end_date >= month_start),
        )
        .order_by(Military.name.asc(), Military.nim.asc())
        .all()
    )
    return DiagnosticContext(
        schedule_month=schedule_month,
        schedule_version=schedule_version,
        month_start=month_start,
        month_end=month_end,
        militaries=militaries,
        assignments=Assignment.query.filter_by(schedule_version_id=schedule_version.id).all(),
        teams=Team.query.order_by(Team.code.asc()).all(),
        team_references=TeamCycleReference.query.all(),
        unavailabilities=Unavailability.query.filter(
            Unavailability.start_date <= month_end,
            Unavailability.end_date >= month_start,
        ).all(),
        restrictions=MilitaryRestriction.query.filter(
            MilitaryRestriction.start_date <= month_end,
            or_(MilitaryRestriction.end_date.is_(None), MilitaryRestriction.end_date >= month_start),
        ).all(),
    )


class BaseDiagnosticValidator:
    def validate(self, context: DiagnosticContext) -> list[DiagnosticProblem]:
        raise NotImplementedError


class ConfigurationDiagnosticValidator(BaseDiagnosticValidator):
    def validate(self, context: DiagnosticContext) -> list[DiagnosticProblem]:
        problems = []
        if not context.schedule_month.versions:
            problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.CONFIGURATION, "MONTH_WITHOUT_VERSION", "Mes sem versao", "O mes de escala nao possui versoes.", is_blocking=True))
        for team in context.teams:
            has_reference = any(ref.team_id == team.id for ref in context.team_references)
            has_relevant_patrol = any(_military_has_team_in_month(military, team.id, context) for military in context.militaries)
            if not has_reference:
                level = DiagnosticLevel.ERROR if has_relevant_patrol else DiagnosticLevel.WARNING
                problems.append(problem(level, DiagnosticCategory.CONFIGURATION, "TEAM_MISSING_REFERENCE", f"Equipa {team.code} sem referencia", "A equipa nao possui referencia de ciclo.", team_id=team.id, is_blocking=level == DiagnosticLevel.ERROR))
        problems.extend(_overlapping_references(context.team_references))
        return problems


class MilitaryDiagnosticValidator(BaseDiagnosticValidator):
    def validate(self, context: DiagnosticContext) -> list[DiagnosticProblem]:
        problems = []
        for military in context.militaries:
            if military.end_date and military.end_date < military.start_date:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.MILITARY, "ASSIGNMENT_OUTSIDE_MILITARY_PERIOD", "Periodo do militar invalido", "A data de fim e anterior a data de inicio.", military_id=military.id, is_blocking=True))
            if military.functional_type == FunctionalType.PATRULHEIRO.value and not _military_has_any_team_in_month(military, context):
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.MILITARY, "MILITARY_WITHOUT_TEAM", "Patrulheiro sem equipa", "Nao e possivel calcular corretamente o ciclo durante o mes.", military_id=military.id, suggested_action="Associar equipa ou rever historico."))
            if military.functional_type != FunctionalType.PATRULHEIRO.value and _military_has_any_team_in_month(military, context):
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.MILITARY, "MILITARY-WITH-INVALID-TEAM", "Militar nao patrulheiro associado a equipa", "SEC, SI ou CMD nao devem estar associados a equipa operacional.", military_id=military.id, is_blocking=True))
        return problems


class CycleDiagnosticValidator(BaseDiagnosticValidator):
    def validate(self, context: DiagnosticContext) -> list[DiagnosticProblem]:
        problems = []
        for assignment in visible_assignments(context):
            military = assignment.military
            if military.functional_type != FunctionalType.PATRULHEIRO.value:
                continue
            team = membership_service.get_team_for_military_on_date(military.id, assignment.assignment_date)
            if team is None:
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.CYCLE, "MILITARY_WITHOUT_TEAM", "Atribuicao sem equipa", "Nao existe equipa valida para calcular o ciclo.", assignment, military_id=military.id))
                continue
            try:
                cycle_day = cycle_calculator.calculate_team_day(team, assignment.assignment_date)
            except cycle_calculator.MissingTeamReferenceError:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.CYCLE, "TEAM_MISSING_REFERENCE", "Referencia de ciclo em falta", "Nao foi possivel calcular DS/DC.", assignment, military_id=military.id, team_id=team.id, is_blocking=True))
                continue
            if assignment.code in {"DS", "DC"} and assignment.code != cycle_day.code:
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.CYCLE, "CYCLE_MANUAL_MISMATCH", "DS/DC manual divergente", "O codigo manual nao corresponde ao ciclo calculado.", assignment, military_id=military.id, team_id=team.id, details={"cycle_code": cycle_day.code}))
            if cycle_day.code in {"DS", "DC"} and assignment.code != cycle_day.code:
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.CYCLE, "CYCLE_MANUAL_REST_DAY", f"Servico em {cycle_day.code}", "Existe atribuicao manual em dia de folga do ciclo.", assignment, military_id=military.id, team_id=team.id, details={"cycle_code": cycle_day.code}))
        return problems


class UnavailabilityDiagnosticValidator(BaseDiagnosticValidator):
    def validate(self, context: DiagnosticContext) -> list[DiagnosticProblem]:
        problems = []
        for assignment in visible_assignments(context):
            for unavailability in _unavailabilities_for_assignment(assignment, context):
                if unavailability.status == UnavailabilityStatus.CANCELLED.value:
                    problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.UNAVAILABILITY, "UNAV-CANCELLED-IGNORED", "Indisponibilidade cancelada ignorada", "A indisponibilidade cancelada nao gera conflito.", assignment, military_id=assignment.military_id))
                elif unavailability.status == UnavailabilityStatus.PLANNED.value:
                    problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.UNAVAILABILITY, "UNAV_PLANNED_ASSIGNMENT", "Atribuicao com indisponibilidade planeada", "Existe indisponibilidade planeada na data.", assignment, military_id=assignment.military_id))
                elif unavailability.code == "BM":
                    problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.UNAVAILABILITY, "UNAV_BM_CONFLICT", "BM confirmada com atribuicao", "Baixa medica confirmada impede servico operacional.", assignment, military_id=assignment.military_id, is_blocking=True))
                elif assignment.code not in UNAVAILABILITY_ASSIGNMENT_CODES:
                    problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.UNAVAILABILITY, "UNAV_CONFIRMED_CONFLICT", "Indisponibilidade confirmada com atribuicao", "Existe atribuicao manual incompativel com indisponibilidade confirmada.", assignment, military_id=assignment.military_id, is_blocking=not assignment.has_override))
        for unavailability in context.unavailabilities:
            if unavailability.compensation_status == CompensationStatus.PENDING_DECISION.value:
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.COMPENSATION, "COMPENSATION-PENDING", "Compensacao pendente", "Existe indisponibilidade com compensacao pendente.", assignment_date=unavailability.start_date, military_id=unavailability.military_id))
        return problems


class RestrictionDiagnosticValidator(BaseDiagnosticValidator):
    def validate(self, context: DiagnosticContext) -> list[DiagnosticProblem]:
        problems = []
        for assignment in visible_assignments(context):
            if assignment.code not in OPERATIONAL_ASSIGNMENT_CODES:
                continue
            restrictions = [
                restriction
                for restriction in restriction_service.get_active_restrictions_for_military_on_date(assignment.military_id, assignment.assignment_date)
                if restriction.applies_to_weekday(assignment.assignment_date.weekday())
            ]
            if restrictions:
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.RESTRICTION, "RESTRICTION_CONFLICT", "Restricao aplicavel", "A atribuicao manual coincide com restricao individual.", assignment, military_id=assignment.military_id, is_blocking=False))
                if assignment.has_override:
                    problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.RESTRICTION, "ASSIGNMENT_OVERRIDE", "Override registado", "Existe override associado ao conflito.", assignment, military_id=assignment.military_id))
        return problems


class AssignmentDiagnosticValidator(BaseDiagnosticValidator):
    def validate(self, context: DiagnosticContext) -> list[DiagnosticProblem]:
        problems = []
        for assignment in context.assignments:
            if assignment.is_cleared:
                continue
            if assignment.code not in ALLOWED_ASSIGNMENT_CODES:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.ASSIGNMENT, "ASSIGNMENT_INVALID_CODE", "Codigo invalido", "A atribuicao possui codigo fora do catalogo.", assignment, military_id=assignment.military_id, is_blocking=True))
            if not (context.month_start <= assignment.assignment_date <= context.month_end):
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.ASSIGNMENT, "ASSIGNMENT_OUTSIDE_MONTH", "Atribuicao fora do mes", "A data da atribuicao nao pertence ao mes da versao.", assignment, military_id=assignment.military_id, is_blocking=True))
            if not _military_in_period(assignment.military, assignment.assignment_date):
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.ASSIGNMENT, "ASSIGNMENT_OUTSIDE_MILITARY_PERIOD", "Atribuicao fora do periodo do militar", "O militar nao estava integrado nesta data.", assignment, military_id=assignment.military_id, is_blocking=True))
            if assignment.is_locked:
                problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.ASSIGNMENT, "ASSIGNMENT_LOCKED", "Celula bloqueada", "A atribuicao manual esta protegida.", assignment, military_id=assignment.military_id))
            else:
                problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.ASSIGNMENT, "ASSIGNMENT_UNLOCKED", "Celula desbloqueada", "A atribuicao manual pode ser alterada.", assignment, military_id=assignment.military_id))
            if assignment.has_override:
                level = DiagnosticLevel.WARNING if not assignment.override_reason else DiagnosticLevel.INFO
                code_key = "ASSIGNMENT_OVERRIDE_WITHOUT_REASON" if not assignment.override_reason else "ASSIGNMENT_OVERRIDE"
                problems.append(problem(level, DiagnosticCategory.ASSIGNMENT, code_key, "Override manual", "A atribuicao possui override.", assignment, military_id=assignment.military_id, is_blocking=not assignment.override_reason))
            if assignment.code in {"FF", "FC"}:
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.COMPENSATION, "ASSIGNMENT_FF_FC", "FF/FC sem credito funcional", "O codigo manual nao cria nem consome credito.", assignment, military_id=assignment.military_id))
            if assignment.code in {"R", "CR"}:
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.ASSIGNMENT, "ASSIGNMENT_R_CR", "R/CR sem origem formalizada", "Ainda nao existe validacao operacional completa.", assignment, military_id=assignment.military_id))
            if assignment.code in UNAVAILABILITY_ASSIGNMENT_CODES and not _unavailabilities_for_assignment(assignment, context):
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.ASSIGNMENT, "ASSIGNMENT_UNAV_CODE_WITHOUT_RECORD", "Codigo de indisponibilidade sem registo", "Nao existe indisponibilidade correspondente.", assignment, military_id=assignment.military_id))
            if assignment.is_manual and not assignment.changes:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.ASSIGNMENT, "ASSIGNMENT_MISSING_HISTORY", "Atribuicao sem historico", "A atribuicao manual nao possui eventos de historico.", assignment, military_id=assignment.military_id, is_blocking=True))
        if not context.assignments:
            problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.SYSTEM, "SYSTEM_EMPTY_ASSIGNMENTS", "Mes sem atribuicoes", "Nao existem atribuicoes persistidas nesta versao."))
        return problems


class ScheduleStateDiagnosticValidator(BaseDiagnosticValidator):
    def validate(self, context: DiagnosticContext) -> list[DiagnosticProblem]:
        status = context.schedule_version.status
        if status == ScheduleMonthStatus.DRAFT.value:
            return [problem(DiagnosticLevel.INFO, DiagnosticCategory.SCHEDULE_STATE, "STATE_DRAFT", "Versao em rascunho", "A versao permite edicao manual.")]
        if status == ScheduleMonthStatus.NOT_GENERATED.value and context.assignments:
            return [problem(DiagnosticLevel.ERROR, DiagnosticCategory.SCHEDULE_STATE, "STATE_NOT_GENERATED_WITH_VERSION", "Estado incoerente", "Versao NOT_GENERATED possui atribuicoes.", is_blocking=True)]
        return [problem(DiagnosticLevel.INFO, DiagnosticCategory.SCHEDULE_STATE, "STATE_NOT_EDITABLE", "Versao nao editavel", "A edicao normal esta bloqueada neste estado.")]


class CoverageDiagnosticValidator(BaseDiagnosticValidator):
    def validate(self, context: DiagnosticContext) -> list[DiagnosticProblem]:
        problems = []
        by_day_code: dict[tuple[date, str], int] = {}
        for assignment in visible_assignments(context):
            if assignment.code in COVERAGE_TARGETS:
                key = (assignment.assignment_date, assignment.code)
                by_day_code[key] = by_day_code.get(key, 0) + 1
        if _has_completed_generation(context.schedule_version.id):
            current = context.month_start
            while current <= context.month_end:
                for code, target in COVERAGE_TARGETS.items():
                    count = by_day_code.get((current, code), 0)
                    if count < target:
                        problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COVERAGE, "COVERAGE_MISSING", "Cobertura AT/PO incompleta", f"{code}: {count}/{target}.", assignment_date=current, is_blocking=True, details={"code": code, "count": count, "target": target, "missing": target - count}))
                    elif count > target:
                        problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.COVERAGE, "COVERAGE_EXCESS", "Cobertura AT/PO acima do minimo", f"{code}: {count}/{target}.", assignment_date=current, details={"code": code, "count": count, "target": target}))
                    else:
                        problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.COVERAGE, "COVERAGE_COMPLETE", "Cobertura AT/PO completa", f"{code}: {count}/{target}.", assignment_date=current, details={"code": code, "count": count, "target": target}))
                current += timedelta(days=1)
            return problems
        for (assignment_date, code), count in sorted(by_day_code.items()):
            target = COVERAGE_TARGETS[code]
            level = DiagnosticLevel.INFO if count <= target else DiagnosticLevel.WARNING
            problems.append(problem(level, DiagnosticCategory.COVERAGE, "COVERAGE_PARTIAL", "Cobertura manual parcial", f"{code}: {count}/{target} atribuicoes manuais registadas. A cobertura completa ainda nao e validada automaticamente.", assignment_date=assignment_date, details={"code": code, "count": count, "target": target}))
        return problems


class RestDiagnosticValidator(BaseDiagnosticValidator):
    def validate(self, context: DiagnosticContext) -> list[DiagnosticProblem]:
        problems = []
        assignments_by_military: dict[int, list[Assignment]] = {}
        for assignment in visible_assignments(context):
            assignments_by_military.setdefault(assignment.military_id, []).append(assignment)
        for military_id, assignments in assignments_by_military.items():
            timed = [item for item in assignments if item.code in SERVICE_TIME_WINDOWS]
            untimed = [item for item in assignments if item.code not in SERVICE_TIME_WINDOWS]
            for assignment in untimed:
                problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.REST, "REST_NOT_YET_VALIDATED", "Descanso nao avaliado", "O codigo nao possui horario formalizado nesta versao.", assignment, military_id=military_id))
            intervals = sorted(
                (_assignment_interval(item), item) for item in timed
            )
            for index in range(1, len(intervals)):
                previous_end = intervals[index - 1][0][1]
                current_start = intervals[index][0][0]
                rest = current_start - previous_end
                if rest < timedelta(hours=8):
                    assignment = intervals[index][1]
                    problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.REST, "REST_TOO_SHORT", "Descanso inferior a oito horas", "A diferenca entre atribuicoes manuais e inferior ao minimo.", assignment, military_id=military_id, details={"minutes": int(rest.total_seconds() // 60)}))
        return problems


def problem(level, category, code_key, title, description, assignment: Assignment | None = None, **kwargs) -> DiagnosticProblem:
    return DiagnosticProblem(
        level=level.value if hasattr(level, "value") else level,
        category=category.value if hasattr(category, "value") else category,
        code=DIAG_CODES.get(code_key, code_key),
        title=title,
        description=description,
        assignment_date=kwargs.pop("assignment_date", assignment.assignment_date if assignment else None),
        assignment_id=kwargs.pop("assignment_id", assignment.id if assignment else None),
        **kwargs,
    )


def visible_assignments(context: DiagnosticContext) -> list[Assignment]:
    return [assignment for assignment in context.assignments if assignment.is_visible]


def deduplicate(problems: list[DiagnosticProblem]) -> list[DiagnosticProblem]:
    seen = set()
    unique = []
    for item in problems:
        if item.identity not in seen:
            seen.add(item.identity)
            unique.append(item)
    return unique


def summarize(problems: list[DiagnosticProblem]) -> DiagnosticSummary:
    return DiagnosticSummary(
        total_errors=sum(1 for item in problems if item.level == DiagnosticLevel.ERROR.value),
        total_warnings=sum(1 for item in problems if item.level == DiagnosticLevel.WARNING.value),
        total_infos=sum(1 for item in problems if item.level == DiagnosticLevel.INFO.value),
        has_blocking_errors=any(item.is_blocking for item in problems),
        affected_categories=sorted({item.category for item in problems}),
    )


def issue_from_problem(diagnostic_run: DiagnosticRun, problem_item: DiagnosticProblem) -> DiagnosticIssue:
    return DiagnosticIssue(
        diagnostic_run=diagnostic_run,
        level=problem_item.level,
        category=problem_item.category,
        code=problem_item.code,
        title=problem_item.title,
        description=problem_item.description,
        assignment_date=problem_item.assignment_date,
        military_id=problem_item.military_id,
        team_id=problem_item.team_id,
        assignment_id=problem_item.assignment_id,
        is_blocking=problem_item.is_blocking,
        suggested_action=problem_item.suggested_action,
        details_json=json.dumps(problem_item.details, sort_keys=True, default=str) if problem_item.details else None,
    )


def latest_run(schedule_version_id: int) -> DiagnosticRun | None:
    return (
        DiagnosticRun.query.filter_by(schedule_version_id=schedule_version_id)
        .order_by(DiagnosticRun.created_at.desc(), DiagnosticRun.id.desc())
        .first()
    )


def _has_completed_generation(schedule_version_id: int) -> bool:
    return db.session.query(
        GenerationRun.query.filter(
            GenerationRun.schedule_version_id == schedule_version_id,
            GenerationRun.status.in_(
                [
                    GenerationRunStatus.COMPLETED.value,
                    GenerationRunStatus.COMPLETED_WITH_WARNINGS.value,
                ]
            ),
        ).exists()
    ).scalar()


def problem_sort_key(item: DiagnosticProblem) -> tuple:
    level_order = {DiagnosticLevel.ERROR.value: 0, DiagnosticLevel.WARNING.value: 1, DiagnosticLevel.INFO.value: 2}
    return (level_order[item.level], item.category, item.assignment_date or date.min, item.military_id or 0, item.code)


def _military_in_period(military: Military, assignment_date: date) -> bool:
    return military.start_date <= assignment_date and (military.end_date is None or assignment_date <= military.end_date)


def _military_has_team_in_month(military: Military, team_id: int, context: DiagnosticContext) -> bool:
    return any(
        membership.military_id == military.id
        and membership.team_id == team_id
        and membership.start_date <= context.month_end
        and (membership.end_date is None or membership.end_date >= context.month_start)
        for membership in military.team_memberships
    )


def _military_has_any_team_in_month(military: Military, context: DiagnosticContext) -> bool:
    return any(
        membership.start_date <= context.month_end and (membership.end_date is None or membership.end_date >= context.month_start)
        for membership in military.team_memberships
    )


def _overlapping_references(references: list[TeamCycleReference]) -> list[DiagnosticProblem]:
    problems = []
    by_team: dict[int, list[TeamCycleReference]] = {}
    for reference in references:
        by_team.setdefault(reference.team_id, []).append(reference)
        if reference.reference_phase not in range(1, 7):
            problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.CYCLE, "CYCLE-INVALID-PHASE", "Fase invalida", "A fase da referencia deve estar entre 1 e 6.", team_id=reference.team_id, is_blocking=True))
    for team_id, items in by_team.items():
        ordered = sorted(items, key=lambda item: item.valid_from)
        for previous, current in zip(ordered, ordered[1:]):
            previous_until = previous.valid_until or date.max
            if current.valid_from <= previous_until:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.CYCLE, "CONFIG-MISSING-CYCLE-REFERENCE", "Referencias sobrepostas", "Existem referencias de ciclo sobrepostas.", team_id=team_id, is_blocking=True))
    return problems


def _unavailabilities_for_assignment(assignment: Assignment, context: DiagnosticContext) -> list[Unavailability]:
    matches = []
    for unavailability in context.unavailabilities:
        if unavailability.military_id != assignment.military_id:
            continue
        if unavailability.start_date <= assignment.assignment_date <= unavailability.end_date:
            matches.append(unavailability)
    return sorted(matches, key=lambda item: (0 if item.status == UnavailabilityStatus.CONFIRMED.value else 1, item.start_date, item.id))


def _assignment_interval(assignment: Assignment) -> tuple[datetime, datetime]:
    window = SERVICE_TIME_WINDOWS[assignment.code]
    start = datetime.combine(assignment.assignment_date, window.start_time)
    end_date = assignment.assignment_date + timedelta(days=1) if window.crosses_midnight else assignment.assignment_date
    end = datetime.combine(end_date, window.end_time)
    return start, end
