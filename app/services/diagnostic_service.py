import json
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy import or_

from app.extensions import db
from app.models import (
    Assignment,
    AssignmentChange,
    AssignmentSource,
    CompensationStatus,
    CompensatoryLeaveCredit,
    CompensatoryLeaveCreditStatus,
    DiagnosticCategory,
    DiagnosticIssue,
    DiagnosticLevel,
    DiagnosticRun,
    DiagnosticRunStatus,
    FunctionalType,
    GenerationRun,
    GenerationRunStatus,
    Holiday,
    HolidayLeaveCredit,
    HolidayLeaveCreditStatus,
    Military,
    MilitaryRestriction,
    MilitaryTeamHistory,
    ScheduleMonth,
    ScheduleMonthStatus,
    ScheduleVersion,
    ScheduleVersionStateEvent,
    ScheduleVersionStateEventType,
    RescheduledRestCredit,
    RescheduledRestCreditStatus,
    Team,
    TeamCycleReference,
    Unavailability,
    UnavailabilityStatus,
)
from app.models.military import utc_now
from app.services import cycle_calculator
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
    "STATE_VALIDATED": "STATE-VALIDATED",
    "STATE_PUBLISHED": "STATE-PUBLISHED",
    "STATE_CLOSED": "STATE-CLOSED",
    "STATE_VALIDATION_WITHOUT_DIAGNOSTIC": "STATE-VALIDATION-WITHOUT-DIAGNOSTIC",
    "STATE_PUBLICATION_WITHOUT_VALIDATION": "STATE-PUBLICATION-WITHOUT-VALIDATION",
    "STATE_REVISION_CHANGED": "STATE-VALIDATED-REVISION-CHANGED",
    "STATE_TWO_PUBLISHED": "STATE-TWO-PUBLISHED",
    "STATE_CLOSED_WITHOUT_EVENT": "STATE-CLOSED-WITHOUT-EVENT",
    "STATE_MONTH_PUBLISHED_INCOHERENT": "STATE-PUBLISHED-VERSION-INCOHERENT",
    "STATE_VALIDATED_LONG": "STATE-VALIDATED-LONG",
    "STATE_MONTH_ENDED_NOT_CLOSED": "STATE-MONTH-ENDED-NOT-CLOSED",
    "STATE_EARLY_CLOSE": "STATE-EARLY-CLOSE",
    "STATE_OFFICIAL_VERSION": "STATE-OFFICIAL-VERSION",
    "COVERAGE_PARTIAL": "COVERAGE-PARTIAL-MANUAL",
    "COVERAGE_COMPLETE": "COVERAGE-COMPLETE",
    "COVERAGE_MISSING": "COVERAGE-MISSING",
    "COVERAGE_EXCESS": "COVERAGE-EXCESS",
    "REST_TOO_SHORT": "REST-TOO-SHORT",
    "REST_NOT_YET_VALIDATED": "REST-NOT-YET-VALIDATED",
    "SYSTEM_EMPTY_ASSIGNMENTS": "SYSTEM-MONTH-WITHOUT-ASSIGNMENTS",
    "PT_NOT_REQUESTED": "PT-NOT-REQUESTED",
    "PT_NO_SURPLUS": "PT-NOT-CREATED-NO-SURPLUS",
    "PT_INCOMPLETE_COVERAGE": "PT-NOT-CREATED-COVERAGE-INCOMPLETE",
    "PT_MANUAL_MISSING_TIME": "PT-MANUAL-MISSING-TIME",
    "PT_MANUAL_MISSING_DURATION": "PT-MANUAL-MISSING-DURATION",
    "PT_DSDC": "PT-IN-DS-DC",
    "PT_AUTO_DSDC": "PT-AUTO-IN-DS-DC",
    "PT_CMD": "PT-CMD",
    "PT_AUTO_UNAV_CONFIRMED": "PT-AUTO-CONFIRMED-UNAVAILABILITY",
    "PT_AUTO_REST_TOO_SHORT": "PT-AUTO-REST-TOO-SHORT",
    "PT_INVALID_INTERVAL": "PT-INVALID-INTERVAL",
    "PT_DAILY_LIMIT_EXCEEDED": "PT-DAILY-LIMIT-EXCEEDED",
    "FF_DUPLICATE_CREDIT": "FF-DUPLICATE-CREDIT",
    "FF_SCHEDULED_WITHOUT_CELL": "FF-SCHEDULED-WITHOUT-CELL",
    "FF_CELL_WITHOUT_CREDIT": "FF-CELL-WITHOUT-CREDIT",
    "FF_SCHEDULED_DSDC": "FF-SCHEDULED-IN-DS-DC",
    "FF_SCHEDULED_CONFIRMED_UNAV": "FF-SCHEDULED-CONFIRMED-UNAVAILABILITY",
    "FF_USED_WITHOUT_EFFECTIVE_DATE": "FF-USED-WITHOUT-EFFECTIVE-DATE",
    "FF_INCOHERENT_STATUS": "FF-INCOHERENT-STATUS",
    "FF_CELL_CHANGED": "FF-CELL-CHANGED-WITHOUT-CREDIT-UPDATE",
    "FF_UNPROCESSED_RIGHT": "FF-POTENTIAL-RIGHT-UNPROCESSED",
    "FF_PENDING_LONG": "FF-PENDING-LONG",
    "FF_PLANNED_UNAV": "FF-SCHEDULED-PLANNED-UNAVAILABILITY",
    "FF_DIFFERENT_VERSION": "FF-SCHEDULED-DIFFERENT-VERSION",
    "FF_INACTIVE_HOLIDAY": "FF-INACTIVE-HOLIDAY-WITH-CREDITS",
    "FF_PENDING_INFO": "FF-PENDING",
    "FF_SCHEDULED_INFO": "FF-SCHEDULED",
    "FF_USED_INFO": "FF-USED",
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
    holidays: list[Holiday] = field(default_factory=list)
    holiday_leave_credits: list[HolidayLeaveCredit] = field(default_factory=list)
    compensatory_leave_credits: list[CompensatoryLeaveCredit] = field(default_factory=list)
    rescheduled_rest_credits: list[RescheduledRestCredit] = field(default_factory=list)
    teams_by_id: dict[int, Team] = field(default_factory=dict)
    memberships_by_military: dict[int, list[MilitaryTeamHistory]] = field(default_factory=dict)
    references_by_team: dict[int, list[TeamCycleReference]] = field(default_factory=dict)
    team_date_cache: dict[tuple[int, date], Team | None] = field(default_factory=dict)
    cycle_cache: dict[tuple[int, date], cycle_calculator.CycleDay] = field(default_factory=dict)

    def team_for_military_on_date(self, military_id: int, assignment_date: date) -> Team | None:
        key = (military_id, assignment_date)
        if key not in self.team_date_cache:
            membership = next(
                (
                    item
                    for item in self.memberships_by_military.get(military_id, [])
                    if item.start_date <= assignment_date and (item.end_date is None or item.end_date >= assignment_date)
                ),
                None,
            )
            self.team_date_cache[key] = self.teams_by_id.get(membership.team_id) if membership else None
        return self.team_date_cache[key]

    def cycle_day_for_team(self, team: Team, assignment_date: date) -> cycle_calculator.CycleDay:
        key = (team.id, assignment_date)
        if key in self.cycle_cache:
            return self.cycle_cache[key]
        reference = next(
            (
                item
                for item in self.references_by_team.get(team.id, [])
                if item.valid_from <= assignment_date and (item.valid_until is None or item.valid_until >= assignment_date)
            ),
            None,
        )
        if reference is None:
            raise cycle_calculator.MissingTeamReferenceError(
                {"reference": "A equipa nao possui referencia valida para a data indicada."}
            )
        phase = cycle_calculator.calculate_phase(reference.reference_phase, reference.reference_date, assignment_date)
        code = cycle_calculator.day_off_code_for_phase(phase, assignment_date)
        self.cycle_cache[key] = cycle_calculator.CycleDay(
            day=assignment_date,
            weekday_name=cycle_calculator.WEEKDAY_NAMES[assignment_date.weekday()],
            phase=phase,
            code=code,
            explanation=cycle_calculator.explain_calculation(reference, assignment_date, phase, code),
        )
        return self.cycle_cache[key]


class ScheduleDiagnosticService:
    def __init__(self, validators: list | None = None):
        self.validators = validators or [
            ConfigurationDiagnosticValidator(),
            MilitaryDiagnosticValidator(),
            CycleDiagnosticValidator(),
            UnavailabilityDiagnosticValidator(),
            RestrictionDiagnosticValidator(),
            AssignmentDiagnosticValidator(),
            HolidayLeaveDiagnosticValidator(),
            CompensationDiagnosticValidator(),
            PTDiagnosticValidator(),
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
    military_ids = [military.id for military in militaries]
    memberships = (
        MilitaryTeamHistory.query.filter(
            MilitaryTeamHistory.military_id.in_(military_ids),
            MilitaryTeamHistory.start_date <= month_end,
            or_(MilitaryTeamHistory.end_date.is_(None), MilitaryTeamHistory.end_date >= month_start),
        )
        .order_by(MilitaryTeamHistory.start_date.desc(), MilitaryTeamHistory.id.desc())
        .all()
    ) if military_ids else []
    teams = Team.query.order_by(Team.code.asc()).all()
    team_references = TeamCycleReference.query.all()
    return DiagnosticContext(
        schedule_month=schedule_month,
        schedule_version=schedule_version,
        month_start=month_start,
        month_end=month_end,
        militaries=militaries,
        assignments=Assignment.query.filter_by(schedule_version_id=schedule_version.id).all(),
        teams=teams,
        team_references=team_references,
        unavailabilities=Unavailability.query.filter(
            Unavailability.start_date <= month_end,
            Unavailability.end_date >= month_start,
        ).all(),
        restrictions=MilitaryRestriction.query.filter(
            MilitaryRestriction.start_date <= month_end,
            or_(MilitaryRestriction.end_date.is_(None), MilitaryRestriction.end_date >= month_start),
        ).all(),
        holidays=Holiday.query.filter(
            Holiday.holiday_date >= month_start,
            Holiday.holiday_date <= month_end,
        ).all(),
        holiday_leave_credits=HolidayLeaveCredit.query.all(),
        compensatory_leave_credits=CompensatoryLeaveCredit.query.all(),
        rescheduled_rest_credits=RescheduledRestCredit.query.all(),
        teams_by_id={team.id: team for team in teams},
        memberships_by_military=_group_by_military(memberships),
        references_by_team=_group_by_team(team_references),
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
            team = context.team_for_military_on_date(military.id, assignment.assignment_date)
            if team is None:
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.CYCLE, "MILITARY_WITHOUT_TEAM", "Atribuicao sem equipa", "Nao existe equipa valida para calcular o ciclo.", assignment, military_id=military.id))
                continue
            try:
                cycle_day = context.cycle_day_for_team(team, assignment.assignment_date)
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
                for restriction in context.restrictions
                if restriction.military_id == assignment.military_id
                and restriction.start_date <= assignment.assignment_date
                and (restriction.end_date is None or restriction.end_date >= assignment.assignment_date)
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
            if assignment.code == "FF" and assignment.holiday_leave_credit_id is None:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FF_CELL_WITHOUT_CREDIT", "FF sem credito", "Existe celula FF sem ligacao a credito.", assignment, military_id=assignment.military_id, is_blocking=True))
            if assignment.code == "FC" and assignment.compensatory_leave_credit_id is None:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FC-CELL-WITHOUT-CREDIT", "FC sem credito", "Existe celula FC sem ligacao a credito.", assignment, military_id=assignment.military_id, is_blocking=True))
            if assignment.code == "FR" and assignment.rescheduled_rest_credit_id is None:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FR-CELL-WITHOUT-CREDIT", "FR sem direito", "Existe celula FR sem ligacao a direito.", assignment, military_id=assignment.military_id, is_blocking=True))
            if assignment.code in {"R", "CR"}:
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.ASSIGNMENT, "ASSIGNMENT_R_CR", "R/CR sem origem formalizada", "Ainda nao existe validacao operacional completa.", assignment, military_id=assignment.military_id))
            if assignment.code in UNAVAILABILITY_ASSIGNMENT_CODES and not _unavailabilities_for_assignment(assignment, context):
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.ASSIGNMENT, "ASSIGNMENT_UNAV_CODE_WITHOUT_RECORD", "Codigo de indisponibilidade sem registo", "Nao existe indisponibilidade correspondente.", assignment, military_id=assignment.military_id))
            if assignment.is_manual and not assignment.changes:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.ASSIGNMENT, "ASSIGNMENT_MISSING_HISTORY", "Atribuicao sem historico", "A atribuicao manual nao possui eventos de historico.", assignment, military_id=assignment.military_id, is_blocking=True))
        if not context.assignments:
            problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.SYSTEM, "SYSTEM_EMPTY_ASSIGNMENTS", "Mes sem atribuicoes", "Nao existem atribuicoes persistidas nesta versao."))
        return problems


class HolidayLeaveDiagnosticValidator(BaseDiagnosticValidator):
    def validate(self, context: DiagnosticContext) -> list[DiagnosticProblem]:
        problems = []
        visible = visible_assignments(context)
        credits_by_id = {credit.id: credit for credit in context.holiday_leave_credits}
        assignments_by_credit: dict[int, list[Assignment]] = {}
        for assignment in visible:
            if assignment.holiday_leave_credit_id is not None:
                assignments_by_credit.setdefault(assignment.holiday_leave_credit_id, []).append(assignment)
                if assignment.code != "FF":
                    problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FF_CELL_CHANGED", "Celula FF alterada", "A celula ligada a credito FF deixou de possuir codigo FF.", assignment, military_id=assignment.military_id, is_blocking=True))
            if assignment.code == "FF" and assignment.holiday_leave_credit_id is None:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FF_CELL_WITHOUT_CREDIT", "FF sem credito", "Existe celula FF sem ligacao a credito.", assignment, military_id=assignment.military_id, is_blocking=True))

        source_counts: dict[int, int] = {}
        for credit in context.holiday_leave_credits:
            source_counts[credit.source_assignment_id] = source_counts.get(credit.source_assignment_id, 0) + 1
        for credit in context.holiday_leave_credits:
            if source_counts.get(credit.source_assignment_id, 0) > 1:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FF_DUPLICATE_CREDIT", "Credito FF duplicado", "A mesma atribuicao de origem possui mais do que uma FF.", assignment_date=credit.service_date, military_id=credit.military_id, is_blocking=True, details={"source_assignment_id": credit.source_assignment_id}))
            if credit.holiday and not credit.holiday.is_active:
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.COMPENSATION, "FF_INACTIVE_HOLIDAY", "Feriado inativo com FF", "O feriado foi desativado, mas os direitos adquiridos permanecem preservados.", assignment_date=credit.service_date, military_id=credit.military_id, details={"holiday_id": credit.holiday_id}))
            if credit.status == HolidayLeaveCreditStatus.PENDING.value:
                problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.COMPENSATION, "FF_PENDING_INFO", "FF pendente", "Existe FF pendente de agendamento.", assignment_date=credit.service_date, military_id=credit.military_id))
                if (context.month_end - credit.service_date).days > 30:
                    problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.COMPENSATION, "FF_PENDING_LONG", "FF pendente prolongada", "A FF esta pendente ha mais de um mes.", assignment_date=credit.service_date, military_id=credit.military_id))
            if credit.status in {HolidayLeaveCreditStatus.SCHEDULED.value, HolidayLeaveCreditStatus.RESCHEDULED.value}:
                problems.extend(_scheduled_ff_problems(credit, assignments_by_credit.get(credit.id, []), context))
            if credit.status == HolidayLeaveCreditStatus.USED.value:
                problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.COMPENSATION, "FF_USED_INFO", "FF gozada", "O gozo da FF esta confirmado.", assignment_date=credit.effective_date or credit.scheduled_date, military_id=credit.military_id))
                if credit.effective_date is None:
                    problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FF_USED_WITHOUT_EFFECTIVE_DATE", "FF gozada sem data efetiva", "Uma FF gozada deve possuir data efetiva.", assignment_date=credit.scheduled_date, military_id=credit.military_id, is_blocking=True))
            if _credit_status_is_incoherent(credit):
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FF_INCOHERENT_STATUS", "Estado FF incoerente", "O estado da FF nao corresponde aos seus campos de data.", assignment_date=credit.scheduled_date or credit.service_date, military_id=credit.military_id, is_blocking=True, details={"status": credit.status}))

        processed_source_ids = {credit.source_assignment_id for credit in context.holiday_leave_credits}
        active_holiday_dates = {holiday.holiday_date for holiday in context.holidays if holiday.is_active}
        for assignment in visible:
            if (
                assignment.assignment_date in active_holiday_dates
                and assignment.code in {"AT1", "AT2", "AT3", "PO1", "PO2", "PO3", "PT", "R", "CR"}
                and assignment.id not in processed_source_ids
            ):
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.COMPENSATION, "FF_UNPROCESSED_RIGHT", "Possivel direito FF por processar", "Existe servico elegivel em feriado sem credito FF associado.", assignment, military_id=assignment.military_id))
        return problems


class CompensationDiagnosticValidator(BaseDiagnosticValidator):
    def validate(self, context: DiagnosticContext) -> list[DiagnosticProblem]:
        problems = []
        visible = visible_assignments(context)
        fc_assignments_by_credit: dict[int, list[Assignment]] = {}
        fr_assignments_by_credit: dict[int, list[Assignment]] = {}
        active_holiday_dates = {holiday.holiday_date for holiday in context.holidays if holiday.is_active}

        for assignment in visible:
            if assignment.compensatory_leave_credit_id is not None:
                fc_assignments_by_credit.setdefault(assignment.compensatory_leave_credit_id, []).append(assignment)
                if assignment.code != "FC":
                    problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FC-CELL-CHANGED-WITHOUT-CREDIT-UPDATE", "Celula FC alterada", "A celula ligada a FC deixou de possuir codigo FC.", assignment, military_id=assignment.military_id, is_blocking=True))
            if assignment.rescheduled_rest_credit_id is not None:
                fr_assignments_by_credit.setdefault(assignment.rescheduled_rest_credit_id, []).append(assignment)
                if assignment.code != "FR":
                    problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FR-CELL-CHANGED-WITHOUT-CREDIT-UPDATE", "Celula FR alterada", "A celula ligada a FR deixou de possuir codigo FR.", assignment, military_id=assignment.military_id, is_blocking=True))
            if assignment.code == "FC" and assignment.compensatory_leave_credit_id is None:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FC-CELL-WITHOUT-CREDIT", "FC sem credito", "Existe celula FC sem ligacao a credito.", assignment, military_id=assignment.military_id, is_blocking=True))
            if assignment.code == "FR" and assignment.rescheduled_rest_credit_id is None:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FR-CELL-WITHOUT-CREDIT", "FR sem direito", "Existe celula FR sem ligacao a direito.", assignment, military_id=assignment.military_id, is_blocking=True))

        fc_source_keys: dict[tuple, int] = {}
        for credit in context.compensatory_leave_credits:
            key = (
                credit.military_id,
                credit.source_type,
                credit.source_service_date,
                credit.source_service_code,
                credit.unit_number,
            )
            fc_source_keys[key] = fc_source_keys.get(key, 0) + 1
        for credit in context.compensatory_leave_credits:
            assignments = fc_assignments_by_credit.get(credit.id, [])
            if fc_source_keys.get((credit.military_id, credit.source_type, credit.source_service_date, credit.source_service_code, credit.unit_number), 0) > 1:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FC-DUPLICATE-CREDIT", "Credito FC duplicado", "Existe mais do que uma FC para a mesma unidade de origem.", assignment_date=credit.source_service_date, military_id=credit.military_id, is_blocking=True))
            if credit.minutes != 480 or credit.unit_number < 1 or credit.units_from_source < 1:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FC-WRONG-UNITS", "Unidade FC invalida", "Cada FC deve ser uma unidade indivisivel de 480 minutos.", assignment_date=credit.source_service_date, military_id=credit.military_id, is_blocking=True))
            if credit.source_service_code in {"R", "CR"} and credit.source_service_date in active_holiday_dates:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FC-R-CR-CREDIT-ON-HOLIDAY", "FC indevida em feriado", "R/CR em feriado deve gerar apenas potencial FF, nao FC.", assignment_date=credit.source_service_date, military_id=credit.military_id, is_blocking=True))
            if credit.source_type == "COMMANDER_DISCRETION" and not credit.commander_reason:
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.COMPENSATION, "FC-DISCRETION-WITHOUT-REASON", "FC de comando sem motivo", "A decisao de comando deve possuir motivo obrigatorio.", assignment_date=credit.source_service_date, military_id=credit.military_id))
            if credit.status in {CompensatoryLeaveCreditStatus.SCHEDULED.value, CompensatoryLeaveCreditStatus.RESCHEDULED.value}:
                if not assignments:
                    problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FC-SCHEDULED-WITHOUT-CELL", "FC agendada sem celula", "A FC agendada nao possui celula FC visivel ligada.", assignment_date=credit.scheduled_date, military_id=credit.military_id, is_blocking=True))
                for assignment in assignments:
                    problems.extend(_scheduled_compensation_assignment_problems(assignment, context, "FC"))
                if credit.scheduled_date and credit.scheduled_date.year > credit.expires_on.year:
                    problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.COMPENSATION, "FC-SCHEDULED-NEXT-YEAR", "FC agendada no ano seguinte", "A FC foi protegida por agendamento antes da expiracao.", assignment_date=credit.scheduled_date, military_id=credit.military_id))
            if credit.status == CompensatoryLeaveCreditStatus.PENDING.value:
                problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.COMPENSATION, "FC-PENDING", "FC pendente", "Existe FC pendente de agendamento.", assignment_date=credit.source_service_date, military_id=credit.military_id))
                if (credit.expires_on - context.month_end).days <= 30:
                    problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.COMPENSATION, "FC-NEAR-EXPIRY", "FC perto de expirar", "A FC aproxima-se do fim do ano civil.", assignment_date=credit.expires_on, military_id=credit.military_id))
            if credit.status == CompensatoryLeaveCreditStatus.USED.value and credit.effective_date is None:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FC-USED-WITHOUT-EFFECTIVE-DATE", "FC gozada sem data efetiva", "Uma FC gozada deve possuir data efetiva.", assignment_date=credit.scheduled_date, military_id=credit.military_id, is_blocking=True))
            if credit.status == CompensatoryLeaveCreditStatus.EXPIRED.value:
                problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.COMPENSATION, "FC-EXPIRED", "FC expirada", "A FC expirada nao conta para saldo disponivel.", assignment_date=credit.expires_on, military_id=credit.military_id))

        fr_origin_keys: dict[tuple, int] = {}
        for credit in context.rescheduled_rest_credits:
            key = (credit.military_id, credit.original_rest_date, credit.original_rest_type)
            fr_origin_keys[key] = fr_origin_keys.get(key, 0) + 1
        for credit in context.rescheduled_rest_credits:
            assignments = fr_assignments_by_credit.get(credit.id, [])
            if fr_origin_keys.get((credit.military_id, credit.original_rest_date, credit.original_rest_type), 0) > 1:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FR-DUPLICATE-CREDIT", "Direito FR duplicado", "Existe mais do que uma FR para o mesmo militar e folga original.", assignment_date=credit.original_rest_date, military_id=credit.military_id, is_blocking=True))
            if credit.original_rest_type not in {"DS", "DC"}:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FR-ORIGIN-NOT-DS-DC", "Origem FR invalida", "FR so pode nascer de DS ou DC.", assignment_date=credit.original_rest_date, military_id=credit.military_id, is_blocking=True))
            if credit.source_service_code not in {"AT1", "AT2", "AT3", "PO1", "PO2", "PO3", "PT"}:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FR-INVALID-SOURCE-CODE", "Codigo origem FR invalido", "FR so pode nascer de AT/PO/PT.", assignment_date=credit.original_rest_date, military_id=credit.military_id, is_blocking=True))
            if credit.status in {RescheduledRestCreditStatus.SCHEDULED.value, RescheduledRestCreditStatus.RESCHEDULED.value}:
                if not assignments:
                    problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FR-SCHEDULED-WITHOUT-CELL", "FR agendada sem celula", "A FR agendada nao possui celula FR visivel ligada.", assignment_date=credit.scheduled_date, military_id=credit.military_id, is_blocking=True))
                for assignment in assignments:
                    problems.extend(_scheduled_compensation_assignment_problems(assignment, context, "FR"))
            if credit.status == RescheduledRestCreditStatus.PENDING.value:
                problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.COMPENSATION, "FR-PENDING", "FR pendente", "Existe FR pendente de agendamento.", assignment_date=credit.original_rest_date, military_id=credit.military_id))

        processed_fc = {(credit.military_id, credit.source_service_date, credit.source_service_code) for credit in context.compensatory_leave_credits}
        processed_fr = {(credit.military_id, credit.original_rest_date, credit.original_rest_type) for credit in context.rescheduled_rest_credits}
        for assignment in visible:
            if assignment.code in {"R", "CR"} and assignment.assignment_date not in active_holiday_dates:
                if (assignment.military_id, assignment.assignment_date, assignment.code) not in processed_fc:
                    problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.COMPENSATION, "FC-POTENTIAL-RIGHT-UNPROCESSED", "Possivel direito FC por processar", "Existe R/CR sem creditos FC confirmados.", assignment, military_id=assignment.military_id))
            if assignment.code in {"AT1", "AT2", "AT3", "PO1", "PO2", "PO3", "PT"}:
                rest_type = _assignment_cycle_code(assignment, context)
                if rest_type in {"DS", "DC"} and (assignment.military_id, assignment.assignment_date, rest_type) not in processed_fr:
                    problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.COMPENSATION, "FR-POTENTIAL-RIGHT-UNPROCESSED", "Possivel direito FR por processar", "Existe AT/PO/PT em DS/DC sem folga reagendada confirmada.", assignment, military_id=assignment.military_id))
        return problems


class PTDiagnosticValidator(BaseDiagnosticValidator):
    def validate(self, context: DiagnosticContext) -> list[DiagnosticProblem]:
        problems = []
        pt_assignments = [assignment for assignment in visible_assignments(context) if assignment.code == "PT"]
        generation = _latest_generation_for_version(context.schedule_version.id)
        pt_parameters = _pt_parameters(generation)
        pt_summary = _generation_summary(generation)
        if generation and not pt_parameters.get("enabled"):
            problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.SYSTEM, "PT_NOT_REQUESTED", "PT nao solicitado", "A ultima execucao nao solicitou geracao automatica de PT."))
        for assignment_date in pt_summary.get("pt_days_without_surplus", []) or []:
            problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.SYSTEM, "PT_NO_SURPLUS", "PT nao criado", "Nao existiam sobrantes elegiveis para PT.", assignment_date=date.fromisoformat(assignment_date)))
        for assignment_date in pt_summary.get("pt_days_skipped_incomplete_coverage", []) or []:
            problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.COVERAGE, "PT_INCOMPLETE_COVERAGE", "PT bloqueado por cobertura", "PT nao foi criado porque AT/PO estava incompleto.", assignment_date=date.fromisoformat(assignment_date)))
        max_daily = pt_parameters.get("max_daily") or 0
        if max_daily:
            by_day: dict[date, int] = {}
            for assignment in pt_assignments:
                by_day[assignment.assignment_date] = by_day.get(assignment.assignment_date, 0) + 1
            for assignment_date, count in by_day.items():
                if count > max_daily:
                    problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.ASSIGNMENT, "PT_DAILY_LIMIT_EXCEEDED", "PT acima do limite diario", f"Existem {count} PT para limite {max_daily}.", assignment_date=assignment_date, details={"count": count, "max_daily": max_daily}))
        for assignment in pt_assignments:
            interval = _assignment_interval(assignment)
            if assignment.is_manual and (assignment.start_time is None or assignment.end_time is None):
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.ASSIGNMENT, "PT_MANUAL_MISSING_TIME", "PT manual sem horario", "O PT manual nao possui hora inicial e final estruturadas.", assignment, military_id=assignment.military_id))
            if assignment.is_manual and assignment.duration_minutes is None:
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.ASSIGNMENT, "PT_MANUAL_MISSING_DURATION", "PT manual sem duracao", "O PT manual nao possui duracao estruturada.", assignment, military_id=assignment.military_id))
            if interval is None or assignment.duration_minutes not in {360, 480}:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.ASSIGNMENT, "PT_INVALID_INTERVAL", "PT com intervalo invalido", "O PT deve possuir intervalo real e duracao de 6 ou 8 horas.", assignment, military_id=assignment.military_id, is_blocking=assignment.source == AssignmentSource.SYSTEM.value))
            if assignment.military.functional_type == FunctionalType.CMD.value:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.MILITARY, "PT_CMD", "PT atribuido a CMD", "CMD nunca pode executar PT.", assignment, military_id=assignment.military_id, is_blocking=True))
            team = context.team_for_military_on_date(assignment.military_id, assignment.assignment_date)
            if team is not None:
                try:
                    cycle_day = context.cycle_day_for_team(team, assignment.assignment_date)
                    if cycle_day.code in {"DS", "DC"}:
                        level = DiagnosticLevel.ERROR if assignment.source == AssignmentSource.SYSTEM.value else DiagnosticLevel.WARNING
                        code_key = "PT_AUTO_DSDC" if assignment.source == AssignmentSource.SYSTEM.value else "PT_DSDC"
                        problems.append(problem(level, DiagnosticCategory.CYCLE, code_key, f"PT em {cycle_day.code}", "PT coincide com folga DS/DC.", assignment, military_id=assignment.military_id, team_id=team.id, is_blocking=assignment.source == AssignmentSource.SYSTEM.value))
                except cycle_calculator.MissingTeamReferenceError:
                    pass
            if assignment.source == AssignmentSource.SYSTEM.value and interval is not None:
                for unavailability in _unavailabilities_for_assignment(assignment, context):
                    if unavailability.status == UnavailabilityStatus.CONFIRMED.value:
                        problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.UNAVAILABILITY, "PT_AUTO_UNAV_CONFIRMED", "PT automatico em indisponibilidade", "PT automatico coincide com indisponibilidade confirmada.", assignment, military_id=assignment.military_id, is_blocking=True))
                rest_gap = _minimum_rest_gap_for_assignment(assignment, context)
                if rest_gap is not None and rest_gap < timedelta(hours=8):
                    problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.REST, "PT_AUTO_REST_TOO_SHORT", "PT automatico com descanso insuficiente", "PT automatico tem descanso inferior a oito horas.", assignment, military_id=assignment.military_id, is_blocking=True, details={"minutes": int(rest_gap.total_seconds() // 60)}))
        return problems


class ScheduleStateDiagnosticValidator(BaseDiagnosticValidator):
    def validate(self, context: DiagnosticContext) -> list[DiagnosticProblem]:
        problems = []
        status = context.schedule_version.status
        if status == ScheduleMonthStatus.DRAFT.value:
            problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.SCHEDULE_STATE, "STATE_DRAFT", "Versao em rascunho", "A versao permite edicao manual."))
        if status == ScheduleMonthStatus.NOT_GENERATED.value and context.assignments:
            problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.SCHEDULE_STATE, "STATE_NOT_GENERATED_WITH_VERSION", "Estado incoerente", "Versao NOT_GENERATED possui atribuicoes.", is_blocking=True))
        if status == ScheduleMonthStatus.VALIDATED.value:
            problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.SCHEDULE_STATE, "STATE_VALIDATED", "Versao validada", "A versao foi validada e bloqueia edicao normal."))
        if status == ScheduleMonthStatus.PUBLISHED.value:
            problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.SCHEDULE_STATE, "STATE_PUBLISHED", "Versao publicada", "A versao e a referencia oficial do mes quando coerente."))
        if status == ScheduleMonthStatus.CLOSED.value:
            problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.SCHEDULE_STATE, "STATE_CLOSED", "Versao encerrada", "A versao esta fechada e imutavel."))
        if status in {ScheduleMonthStatus.VALIDATED.value, ScheduleMonthStatus.PUBLISHED.value, ScheduleMonthStatus.CLOSED.value}:
            if context.schedule_version.validated_diagnostic_run_id is None:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.SCHEDULE_STATE, "STATE_VALIDATION_WITHOUT_DIAGNOSTIC", "Validacao sem diagnostico", "A versao nao possui diagnostico associado a validacao.", is_blocking=True))
            if context.schedule_version.validated_revision != (context.schedule_version.content_revision or 0):
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.SCHEDULE_STATE, "STATE_REVISION_CHANGED", "Revisao alterada apos validacao", "A revisao de conteudo diverge da revisao validada.", is_blocking=True))
        if status == ScheduleMonthStatus.PUBLISHED.value and context.schedule_version.validated_at is None:
            problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.SCHEDULE_STATE, "STATE_PUBLICATION_WITHOUT_VALIDATION", "Publicacao sem validacao", "A versao publicada nao possui validacao registada.", is_blocking=True))
        published_versions = [
            version
            for version in context.schedule_month.versions
            if version.status == ScheduleMonthStatus.PUBLISHED.value
        ]
        if len(published_versions) > 1:
            problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.SCHEDULE_STATE, "STATE_TWO_PUBLISHED", "Mais do que uma versao publicada", "O mes possui varias versoes publicadas.", is_blocking=True))
        if context.schedule_month.published_version_id:
            official_ids = {version.id for version in published_versions}
            if context.schedule_month.published_version_id not in official_ids:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.SCHEDULE_STATE, "STATE_MONTH_PUBLISHED_INCOHERENT", "Versao oficial incoerente", "O mes aponta para uma versao que nao esta publicada.", is_blocking=True))
            elif context.schedule_version.id == context.schedule_month.published_version_id:
                problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.SCHEDULE_STATE, "STATE_OFFICIAL_VERSION", "Versao oficial", "Esta versao e a versao oficial publicada do mes."))
        if status == ScheduleMonthStatus.CLOSED.value:
            close_event = ScheduleVersionStateEvent.query.filter_by(
                schedule_version_id=context.schedule_version.id,
                event_type=ScheduleVersionStateEventType.CLOSED.value,
            ).first()
            if close_event is None:
                problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.SCHEDULE_STATE, "STATE_CLOSED_WITHOUT_EVENT", "Encerramento sem evento", "A versao fechada nao possui evento de encerramento.", is_blocking=True))
            elif context.schedule_version.closed_at and context.schedule_version.closed_at.date() <= context.month_end:
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.SCHEDULE_STATE, "STATE_EARLY_CLOSE", "Encerramento antecipado", "A escala foi encerrada antes do fim do mes."))
        if status == ScheduleMonthStatus.VALIDATED.value and context.schedule_version.validated_at:
            if utc_now() - context.schedule_version.validated_at > timedelta(days=30):
                problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.SCHEDULE_STATE, "STATE_VALIDATED_LONG", "Validada sem publicacao", "A versao esta validada ha mais de 30 dias sem publicacao."))
        if context.month_end < date.today() and status == ScheduleMonthStatus.PUBLISHED.value:
            problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.SCHEDULE_STATE, "STATE_MONTH_ENDED_NOT_CLOSED", "Mes terminado sem encerramento", "A versao publicada ainda nao foi encerrada."))
        if status not in {ScheduleMonthStatus.DRAFT.value, ScheduleMonthStatus.NOT_GENERATED.value}:
            problems.append(problem(DiagnosticLevel.INFO, DiagnosticCategory.SCHEDULE_STATE, "STATE_NOT_EDITABLE", "Versao nao editavel", "A edicao normal esta bloqueada neste estado."))
        return problems


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
            timed = [item for item in assignments if _assignment_interval(item) is not None]
            untimed = [item for item in assignments if _assignment_interval(item) is None]
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


def _scheduled_compensation_assignment_problems(
    assignment: Assignment,
    context: DiagnosticContext,
    prefix: str,
) -> list[DiagnosticProblem]:
    problems = []
    rest_type = _assignment_cycle_code(assignment, context)
    if rest_type in {"DS", "DC"}:
        problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, f"{prefix}-SCHEDULED-IN-DS-DC", f"{prefix} em DS/DC", f"{prefix} foi agendada em dia de descanso {rest_type}.", assignment, military_id=assignment.military_id, is_blocking=True))
    for unavailability in _unavailabilities_for_assignment(assignment, context):
        if unavailability.status == UnavailabilityStatus.CONFIRMED.value:
            problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, f"{prefix}-SCHEDULED-CONFIRMED-UNAVAILABILITY", f"{prefix} em indisponibilidade", f"{prefix} coincide com indisponibilidade confirmada.", assignment, military_id=assignment.military_id, is_blocking=True))
        elif unavailability.status == UnavailabilityStatus.PLANNED.value:
            problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.COMPENSATION, f"{prefix}-SCHEDULED-PLANNED-UNAVAILABILITY", f"{prefix} em indisponibilidade planeada", f"{prefix} coincide com indisponibilidade planeada.", assignment, military_id=assignment.military_id))
    return problems


def _assignment_cycle_code(assignment: Assignment, context: DiagnosticContext) -> str | None:
    if assignment.military.functional_type != FunctionalType.PATRULHEIRO.value:
        return None
    team = context.team_for_military_on_date(assignment.military_id, assignment.assignment_date)
    if team is None:
        return None
    try:
        return context.cycle_day_for_team(team, assignment.assignment_date).code
    except cycle_calculator.MissingTeamReferenceError:
        return None


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


def _latest_generation_for_version(schedule_version_id: int) -> GenerationRun | None:
    return (
        GenerationRun.query.filter_by(schedule_version_id=schedule_version_id)
        .order_by(GenerationRun.created_at.desc(), GenerationRun.id.desc())
        .first()
    )


def _pt_parameters(generation: GenerationRun | None) -> dict:
    if generation is None or not generation.parameters_json:
        return {}
    try:
        return (json.loads(generation.parameters_json).get("pt") or {})
    except json.JSONDecodeError:
        return {}


def _generation_summary(generation: GenerationRun | None) -> dict:
    if generation is None or not generation.summary_json:
        return {}
    try:
        return json.loads(generation.summary_json)
    except json.JSONDecodeError:
        return {}


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
    assignment_interval = _assignment_interval(assignment)
    for unavailability in context.unavailabilities:
        if unavailability.military_id != assignment.military_id:
            continue
        if assignment_interval is not None:
            interval = interval_for_unavailability(unavailability)
            if interval.effective_start < assignment_interval[1] and interval.effective_end > assignment_interval[0]:
                matches.append(unavailability)
        elif unavailability.start_date <= assignment.assignment_date <= unavailability.end_date:
            matches.append(unavailability)
    return sorted(matches, key=lambda item: (0 if item.status == UnavailabilityStatus.CONFIRMED.value else 1, item.start_date, item.id))


def _scheduled_ff_problems(
    credit: HolidayLeaveCredit,
    assignments: list[Assignment],
    context: DiagnosticContext,
) -> list[DiagnosticProblem]:
    problems = [
        problem(
            DiagnosticLevel.INFO,
            DiagnosticCategory.COMPENSATION,
            "FF_SCHEDULED_INFO",
            "FF agendada",
            "Existe FF agendada na escala.",
            assignment_date=credit.scheduled_date,
            military_id=credit.military_id,
        )
    ]
    expected = [
        assignment
        for assignment in assignments
        if assignment.code == "FF"
        and assignment.military_id == credit.military_id
        and assignment.assignment_date == credit.scheduled_date
    ]
    if not expected:
        problems.append(
            problem(
                DiagnosticLevel.ERROR,
                DiagnosticCategory.COMPENSATION,
                "FF_SCHEDULED_WITHOUT_CELL",
                "FF agendada sem celula",
                "O credito esta agendado, mas nao existe celula FF correspondente.",
                assignment_date=credit.scheduled_date,
                military_id=credit.military_id,
                is_blocking=True,
            )
        )
        return problems
    assignment = expected[0]
    if assignment.schedule_version_id != context.schedule_version.id:
        problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.COMPENSATION, "FF_DIFFERENT_VERSION", "FF noutra versao", "A FF esta ligada a uma versao diferente da versao analisada.", assignment, military_id=credit.military_id))
    team = context.team_for_military_on_date(credit.military_id, assignment.assignment_date)
    if team is not None:
        try:
            cycle_day = context.cycle_day_for_team(team, assignment.assignment_date)
        except cycle_calculator.MissingTeamReferenceError:
            cycle_day = None
        if cycle_day and cycle_day.code in {"DS", "DC"}:
            problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FF_SCHEDULED_DSDC", "FF em DS/DC", "A FF esta agendada sobre dia de folga do ciclo.", assignment, military_id=credit.military_id, team_id=team.id, is_blocking=True))
    for unavailability in _unavailabilities_for_assignment(assignment, context):
        if unavailability.status == UnavailabilityStatus.CONFIRMED.value:
            problems.append(problem(DiagnosticLevel.ERROR, DiagnosticCategory.COMPENSATION, "FF_SCHEDULED_CONFIRMED_UNAV", "FF em indisponibilidade confirmada", "A FF coincide com indisponibilidade confirmada.", assignment, military_id=credit.military_id, is_blocking=True))
        elif unavailability.status == UnavailabilityStatus.PLANNED.value:
            problems.append(problem(DiagnosticLevel.WARNING, DiagnosticCategory.COMPENSATION, "FF_PLANNED_UNAV", "FF em indisponibilidade planeada", "A FF coincide com indisponibilidade planeada.", assignment, military_id=credit.military_id))
    return problems


def _credit_status_is_incoherent(credit: HolidayLeaveCredit) -> bool:
    if credit.status == HolidayLeaveCreditStatus.PENDING.value:
        return credit.scheduled_date is not None or credit.effective_date is not None
    if credit.status in {HolidayLeaveCreditStatus.SCHEDULED.value, HolidayLeaveCreditStatus.RESCHEDULED.value}:
        return credit.scheduled_date is None or credit.effective_date is not None
    if credit.status == HolidayLeaveCreditStatus.USED.value:
        return credit.effective_date is None
    if credit.status == HolidayLeaveCreditStatus.CANCELLED.value:
        return not bool((credit.cancellation_reason or "").strip())
    return True


def _assignment_interval(assignment: Assignment) -> tuple[datetime, datetime] | None:
    if assignment.code == "PT":
        if not assignment.start_time or not assignment.duration_minutes:
            return None
        start = datetime.combine(assignment.assignment_date, assignment.start_time)
        return start, start + timedelta(minutes=assignment.duration_minutes)
    if assignment.code not in SERVICE_TIME_WINDOWS:
        return None
    window = SERVICE_TIME_WINDOWS[assignment.code]
    start = datetime.combine(assignment.assignment_date, window.start_time)
    end_date = assignment.assignment_date + timedelta(days=1) if window.crosses_midnight else assignment.assignment_date
    end = datetime.combine(end_date, window.end_time)
    return start, end


def _minimum_rest_gap_for_assignment(target: Assignment, context: DiagnosticContext) -> timedelta | None:
    target_interval = _assignment_interval(target)
    if target_interval is None:
        return None
    target_start, target_end = target_interval
    gaps = []
    for assignment in visible_assignments(context):
        if assignment.id == target.id or assignment.military_id != target.military_id:
            continue
        interval = _assignment_interval(assignment)
        if interval is None:
            continue
        existing_start, existing_end = interval
        if existing_start <= target_start:
            gaps.append(target_start - existing_end)
        else:
            gaps.append(existing_start - target_end)
    return min(gaps) if gaps else None


def _group_by_military(items: list) -> dict[int, list]:
    grouped: dict[int, list] = {}
    for item in items:
        grouped.setdefault(item.military_id, []).append(item)
    return grouped


def _group_by_team(items: list) -> dict[int, list]:
    grouped: dict[int, list] = {}
    for item in items:
        grouped.setdefault(item.team_id, []).append(item)
    return grouped
