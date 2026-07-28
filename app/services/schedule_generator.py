import json
from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy import or_

from app.extensions import db
from app.models import (
    Assignment,
    AssignmentChange,
    AssignmentChangeType,
    AssignmentSelectionDetail,
    AssignmentSource,
    FunctionalType,
    GenerationMode,
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
from app.services import cycle_calculator
from app.services.diagnostic_service import ScheduleDiagnosticService
from app.services.restriction_evaluator import contains, intervals_for_restriction, overlaps as restriction_overlaps
from app.services.service_code_catalog import COVERAGE_TARGETS, SERVICE_TIME_WINDOWS
from app.services.unavailability_evaluator import interval_for_unavailability, overlaps


GENERATION_SERVICE_ORDER = ("AT1", "PO1", "AT2", "PO2", "AT3", "PO3")
GENERATION_SERVICE_CODES = set(GENERATION_SERVICE_ORDER)
MINIMUM_REST_HOURS = 8
DEFAULT_EQUITY_LOOKBACK_MONTHS = 3
NIGHT_SERVICE_CODES = {"AT1", "AT3", "PO1", "PO3"}
EDITABLE_GENERATION_STATUSES = {ScheduleMonthStatus.DRAFT.value}


class ScheduleGenerationError(Exception):
    def __init__(self, message: str, errors: dict[str, str] | None = None):
        super().__init__(message)
        self.errors = errors or {}


@dataclass(frozen=True)
class CandidateMetrics:
    specific_count: int
    total_at_po_count: int
    night_count: int
    weekend_count: int
    consecutive_count: int
    team_load: int
    days_since_equivalent: int
    stable_id: int

    def as_dict(self) -> dict:
        return {
            "specific_count": self.specific_count,
            "total_at_po_count": self.total_at_po_count,
            "night_count": self.night_count,
            "weekend_count": self.weekend_count,
            "consecutive_count": self.consecutive_count,
            "team_load": self.team_load,
            "days_since_equivalent": self.days_since_equivalent,
            "stable_id": self.stable_id,
        }

    def sort_key(self) -> tuple:
        return (
            self.specific_count,
            self.total_at_po_count,
            self.night_count,
            self.weekend_count,
            self.consecutive_count,
            self.team_load,
            -self.days_since_equivalent,
            self.stable_id,
        )


@dataclass(frozen=True)
class CandidateDecision:
    military: Military
    is_eligible: bool
    reason: str
    metrics: CandidateMetrics | None = None
    position: int | None = None
    is_selected: bool = False
    uses_support_group: bool = False


@dataclass(frozen=True)
class SelectionResult:
    assignment_date: date
    service_code: str
    selected: list[CandidateDecision]
    eligible: list[CandidateDecision]
    excluded: list[CandidateDecision]
    required_count: int
    preserved_count: int
    unfilled_count: int
    warnings: list[str] = field(default_factory=list)


@dataclass
class GenerationSummary:
    total_created: int = 0
    total_preserved_manual: int = 0
    total_unfilled: int = 0
    total_warnings: int = 0
    incomplete_services: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    diagnostic_run_id: int | None = None

    def as_dict(self) -> dict:
        return {
            "total_created": self.total_created,
            "total_preserved_manual": self.total_preserved_manual,
            "total_unfilled": self.total_unfilled,
            "total_warnings": self.total_warnings,
            "incomplete_services": self.incomplete_services,
            "warnings": self.warnings,
            "diagnostic_run_id": self.diagnostic_run_id,
        }


@dataclass
class GenerationContext:
    schedule_month: ScheduleMonth
    schedule_version: ScheduleVersion
    month_start: date
    month_end: date
    equity_start: date
    militaries: list[Military]
    assignments: list[Assignment]
    historical_assignments: list[Assignment]
    teams_by_id: dict[int, Team] = field(default_factory=dict)
    memberships_by_military: dict[int, list[MilitaryTeamHistory]] = field(default_factory=dict)
    references_by_team: dict[int, list[TeamCycleReference]] = field(default_factory=dict)
    restrictions_by_military: dict[int, list[MilitaryRestriction]] = field(default_factory=dict)
    unavailabilities_by_military: dict[int, list[Unavailability]] = field(default_factory=dict)
    planned_assignments: list[Assignment] = field(default_factory=list)
    team_load: dict[tuple[date, str, int], int] = field(default_factory=dict)
    team_date_cache: dict[tuple[int, date], Team | None] = field(default_factory=dict)
    cycle_cache: dict[tuple[int, date], cycle_calculator.CycleDay] = field(default_factory=dict)

    @property
    def all_current_assignments(self) -> list[Assignment]:
        return [item for item in self.assignments + self.planned_assignments if item.is_visible]

    @property
    def all_assignment_rows(self) -> list[Assignment]:
        return self.assignments + self.planned_assignments

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

    def confirmed_unavailabilities_for_interval(self, military_id: int, service_start: datetime, service_end: datetime) -> list[Unavailability]:
        matches = []
        for item in self.unavailabilities_by_military.get(military_id, []):
            if item.status != UnavailabilityStatus.CONFIRMED.value:
                continue
            interval = interval_for_unavailability(item)
            if overlaps(interval.effective_start, interval.effective_end, service_start, service_end):
                matches.append(item)
        return matches

    def planned_unavailability_for_interval(self, military_id: int, service_start: datetime, service_end: datetime) -> Unavailability | None:
        for item in self.unavailabilities_by_military.get(military_id, []):
            if item.status != UnavailabilityStatus.PLANNED.value:
                continue
            interval = interval_for_unavailability(item)
            if overlaps(interval.effective_start, interval.effective_end, service_start, service_end):
                return item
        return None

    def restriction_block_reason(self, military_id: int, service_start: datetime, service_end: datetime) -> str | None:
        considered = self.restrictions_by_military.get(military_id, [])
        unavailable_matches = []
        available_intervals = []
        special_intervals = []
        for restriction in considered:
            intervals = intervals_for_restriction(restriction, service_start, service_end)
            if restriction.restriction_type == "UNAVAILABLE":
                unavailable_matches.extend(
                    interval for interval in intervals if restriction_overlaps(interval.start, interval.end, service_start, service_end)
                )
            elif restriction.restriction_type == "AVAILABLE_ONLY":
                available_intervals.extend(intervals)
            elif restriction.restriction_type == "SPECIAL_AVAILABILITY":
                special_intervals.extend(intervals)
        if unavailable_matches:
            return "Existe uma restricao absoluta sobreposta ao intervalo."
        if any(contains(interval.start, interval.end, service_start, service_end) for interval in special_intervals):
            return None
        if any(restriction.restriction_type == "AVAILABLE_ONLY" for restriction in considered):
            if any(contains(interval.start, interval.end, service_start, service_end) for interval in available_intervals):
                return None
            return "Existe disponibilidade limitada e o servico nao esta contido numa janela autorizada."
        return None


class CandidateSelector:
    def select(
        self,
        context: GenerationContext,
        assignment_date: date,
        service_code: str,
        required_count: int,
        preserved_count: int,
    ) -> SelectionResult:
        needed = max(required_count - preserved_count, 0)
        if needed == 0:
            return SelectionResult(
                assignment_date=assignment_date,
                service_code=service_code,
                selected=[],
                eligible=[],
                excluded=[],
                required_count=required_count,
                preserved_count=preserved_count,
                unfilled_count=0,
            )

        selected: list[CandidateDecision] = []
        excluded: list[CandidateDecision] = []
        eligible_snapshot: list[CandidateDecision] = []
        warnings: list[str] = []

        for _ in range(needed):
            candidates, rejected = self._rank_candidates(context, assignment_date, service_code)
            excluded.extend(rejected)
            if not eligible_snapshot:
                eligible_snapshot = candidates
            patrol_candidates = [
                item
                for item in candidates
                if item.military.functional_type == FunctionalType.PATRULHEIRO.value
            ]
            pool = patrol_candidates or candidates
            if not pool:
                break
            chosen = pool[0]
            if chosen.military.functional_type in {FunctionalType.SEC.value, FunctionalType.SI.value}:
                warnings.append(f"{service_code} em {assignment_date.isoformat()} usou {chosen.military.functional_type} por cobertura insuficiente de patrulheiros.")
            selected_decision = CandidateDecision(
                military=chosen.military,
                is_eligible=True,
                reason=chosen.reason,
                metrics=chosen.metrics,
                position=chosen.position,
                is_selected=True,
                uses_support_group=chosen.military.functional_type in {FunctionalType.SEC.value, FunctionalType.SI.value},
            )
            selected.append(selected_decision)
            context.planned_assignments.append(
                Assignment(
                    schedule_version_id=context.schedule_version.id,
                    military_id=chosen.military.id,
                    assignment_date=assignment_date,
                    code=service_code,
                    source=AssignmentSource.SYSTEM.value,
                    is_manual=False,
                    is_locked=False,
                    has_override=False,
                    is_cleared=False,
                )
            )

        return SelectionResult(
            assignment_date=assignment_date,
            service_code=service_code,
            selected=selected,
            eligible=eligible_snapshot,
            excluded=excluded,
            required_count=required_count,
            preserved_count=preserved_count,
            unfilled_count=needed - len(selected),
            warnings=warnings,
        )

    def _rank_candidates(
        self,
        context: GenerationContext,
        assignment_date: date,
        service_code: str,
    ) -> tuple[list[CandidateDecision], list[CandidateDecision]]:
        eligible = []
        excluded = []
        service_start, service_end = service_interval(assignment_date, service_code)
        for military in context.militaries:
            reason = exclusion_reason(context, military, assignment_date, service_code, service_start, service_end)
            if reason:
                excluded.append(CandidateDecision(military=military, is_eligible=False, reason=reason))
                continue
            metrics = build_metrics(context, military, assignment_date, service_code)
            eligible.append(CandidateDecision(military=military, is_eligible=True, reason="Elegivel.", metrics=metrics))
        eligible.sort(key=lambda item: item.metrics.sort_key())
        eligible = [
            CandidateDecision(
                military=item.military,
                is_eligible=True,
                reason=item.reason,
                metrics=item.metrics,
                position=index,
            )
            for index, item in enumerate(eligible, start=1)
        ]
        return eligible, excluded


class ScheduleGenerator:
    def __init__(self, selector: CandidateSelector | None = None):
        self.selector = selector or CandidateSelector()

    def generate_at_po(self, schedule_version: ScheduleVersion) -> GenerationRun:
        validate_generation_target(schedule_version)
        run = GenerationRun(
            schedule_version_id=schedule_version.id,
            source_version_id=schedule_version.id,
            result_version_id=schedule_version.id,
            generation_mode=GenerationMode.FILL_EMPTY.value,
            parameters_json=json.dumps(generation_parameters(), sort_keys=True),
        )
        db.session.add(run)
        db.session.commit()

        return self.generate_into_version(schedule_version, run, commit=True)

    def generate_into_version(
        self,
        schedule_version: ScheduleVersion,
        run: GenerationRun,
        commit: bool = True,
    ) -> GenerationRun:
        summary = GenerationSummary()
        try:
            context = build_generation_context(schedule_version)
            for assignment_date in iter_month_dates(context.month_start, context.month_end):
                for service_code in GENERATION_SERVICE_ORDER:
                    preserved = coverage_count(context, assignment_date, service_code)
                    required = COVERAGE_TARGETS[service_code]
                    if preserved > required:
                        warning = f"{service_code} em {assignment_date.isoformat()} ja possui cobertura acima do minimo ({preserved}/{required})."
                        summary.warnings.append(warning)
                        summary.total_warnings += 1
                        add_no_candidate_detail(run, assignment_date, service_code, warning)
                        continue
                    if preserved:
                        summary.total_preserved_manual += preserved
                    selection = self.selector.select(context, assignment_date, service_code, required, preserved)
                    persist_selection_details(run, selection)
                    for selected in selection.selected:
                        assignment = persist_system_assignment(context, selected.military, assignment_date, service_code)
                        db.session.add(assignment)
                        summary.total_created += 1
                    if selection.unfilled_count:
                        summary.total_unfilled += selection.unfilled_count
                        summary.incomplete_services.append(
                            {
                                "date": assignment_date.isoformat(),
                                "code": service_code,
                                "missing": selection.unfilled_count,
                                "required": required,
                                "preserved": preserved,
                            }
                        )
                    if selection.warnings:
                        summary.warnings.extend(selection.warnings)
                        summary.total_warnings += len(selection.warnings)

            run.status = (
                GenerationRunStatus.COMPLETED_WITH_WARNINGS.value
                if summary.total_unfilled or summary.total_warnings
                else GenerationRunStatus.COMPLETED.value
            )
            run.completed_at = utc_now()
            run.total_created = summary.total_created
            run.total_preserved_manual = summary.total_preserved_manual
            run.total_unfilled = summary.total_unfilled
            run.total_warnings = summary.total_warnings
            run.summary_json = json.dumps(summary.as_dict(), sort_keys=True, default=str)
            if commit:
                db.session.commit()
        except Exception as exc:
            db.session.rollback()
            run = db.session.get(GenerationRun, run.id)
            if run is not None:
                run.status = GenerationRunStatus.FAILED.value
                run.completed_at = utc_now()
                run.summary_json = json.dumps({"error": str(exc)}, sort_keys=True)
                if commit:
                    db.session.commit()
            raise

        if commit:
            diagnostic_run = ScheduleDiagnosticService().run_and_persist(schedule_version)
            run.diagnostic_run_id = diagnostic_run.id
            summary.diagnostic_run_id = diagnostic_run.id
            run.summary_json = json.dumps(summary.as_dict(), sort_keys=True, default=str)
            db.session.commit()
        return run


def build_generation_context(schedule_version: ScheduleVersion, lookback_months: int = DEFAULT_EQUITY_LOOKBACK_MONTHS) -> GenerationContext:
    schedule_month = schedule_version.schedule_month
    month_start = date(schedule_month.year, schedule_month.month, 1)
    month_end = date(schedule_month.year, schedule_month.month, monthrange(schedule_month.year, schedule_month.month)[1])
    equity_start = first_day_months_before(month_start, lookback_months)
    militaries = (
        Military.query.filter(
            Military.start_date <= month_end,
            or_(Military.end_date.is_(None), Military.end_date >= month_start),
        )
        .order_by(Military.id.asc())
        .all()
    )
    military_ids = [military.id for military in militaries]
    assignments = Assignment.query.filter_by(schedule_version_id=schedule_version.id).all()
    historical_assignments = (
        Assignment.query.join(ScheduleVersion, Assignment.schedule_version_id == ScheduleVersion.id)
        .join(ScheduleMonth, ScheduleVersion.schedule_month_id == ScheduleMonth.id)
        .filter(Assignment.assignment_date >= equity_start, Assignment.assignment_date <= month_end)
        .filter(Assignment.is_cleared.is_(False), Assignment.code.in_(GENERATION_SERVICE_CODES))
        .all()
    )
    teams = Team.query.all()
    memberships = (
        MilitaryTeamHistory.query.filter(
            MilitaryTeamHistory.military_id.in_(military_ids),
            MilitaryTeamHistory.start_date <= month_end,
            or_(MilitaryTeamHistory.end_date.is_(None), MilitaryTeamHistory.end_date >= month_start),
        )
        .order_by(MilitaryTeamHistory.start_date.desc(), MilitaryTeamHistory.id.desc())
        .all()
    ) if military_ids else []
    references = (
        TeamCycleReference.query.filter(
            TeamCycleReference.valid_from <= month_end,
            or_(TeamCycleReference.valid_until.is_(None), TeamCycleReference.valid_until >= month_start),
        )
        .order_by(TeamCycleReference.valid_from.desc(), TeamCycleReference.id.desc())
        .all()
    )
    restrictions = (
        MilitaryRestriction.query.filter(
            MilitaryRestriction.military_id.in_(military_ids),
            MilitaryRestriction.is_active.is_(True),
            MilitaryRestriction.start_date <= month_end,
            or_(MilitaryRestriction.end_date.is_(None), MilitaryRestriction.end_date >= month_start - timedelta(days=1)),
        )
        .order_by(MilitaryRestriction.restriction_type.asc(), MilitaryRestriction.id.asc())
        .all()
    ) if military_ids else []
    unavailabilities = (
        Unavailability.query.filter(
            Unavailability.military_id.in_(military_ids),
            Unavailability.is_active.is_(True),
            Unavailability.status != UnavailabilityStatus.CANCELLED.value,
            Unavailability.start_date <= month_end,
            Unavailability.end_date >= month_start - timedelta(days=1),
        )
        .order_by(Unavailability.status.asc(), Unavailability.start_date.asc(), Unavailability.id.asc())
        .all()
    ) if military_ids else []
    return GenerationContext(
        schedule_month=schedule_month,
        schedule_version=schedule_version,
        month_start=month_start,
        month_end=month_end,
        equity_start=equity_start,
        militaries=militaries,
        assignments=assignments,
        historical_assignments=historical_assignments,
        teams_by_id={team.id: team for team in teams},
        memberships_by_military=_group_by_military(memberships),
        references_by_team=_group_by_team(references),
        restrictions_by_military=_group_by_military(restrictions),
        unavailabilities_by_military=_group_by_military(unavailabilities),
    )


def validate_generation_target(schedule_version: ScheduleVersion) -> None:
    if schedule_version.status not in EDITABLE_GENERATION_STATUSES:
        raise ScheduleGenerationError(
            "A versao selecionada nao permite geracao.",
            {"status": "A geracao AT/PO so pode ocorrer em versoes DRAFT."},
        )


def generation_parameters() -> dict:
    return {
        "mode": "complete_empty_cells",
        "service_order": list(GENERATION_SERVICE_ORDER),
        "coverage_targets": COVERAGE_TARGETS,
        "equity_lookback_months": DEFAULT_EQUITY_LOOKBACK_MONTHS,
        "minimum_rest_hours": MINIMUM_REST_HOURS,
        "night_service_codes": sorted(NIGHT_SERVICE_CODES),
    }


def coverage_count(context: GenerationContext, assignment_date: date, service_code: str) -> int:
    return sum(
        1
        for assignment in context.all_current_assignments
        if assignment.assignment_date == assignment_date and assignment.code == service_code
    )


def exclusion_reason(
    context: GenerationContext,
    military: Military,
    assignment_date: date,
    service_code: str,
    service_start: datetime,
    service_end: datetime,
) -> str | None:
    if military.functional_type == FunctionalType.CMD.value:
        return "CMD nao pode receber AT/PO."
    if not military.is_active:
        return "Militar inativo."
    if assignment_date < military.start_date or (military.end_date and assignment_date > military.end_date):
        return "Militar fora do periodo de efetividade."
    if any(
        item.military_id == military.id and item.assignment_date == assignment_date
        for item in context.all_assignment_rows
    ):
        return "Ja existe atribuicao nesta data."
    if military.functional_type == FunctionalType.PATRULHEIRO.value:
        team = context.team_for_military_on_date(military.id, assignment_date)
        if team is None:
            return "Patrulheiro sem equipa valida na data."
        try:
            cycle_day = context.cycle_day_for_team(team, assignment_date)
        except cycle_calculator.MissingTeamReferenceError:
            return "Equipa sem referencia de ciclo valida."
        if cycle_day.code in {"DS", "DC"}:
            return f"Ciclo {cycle_day.code}."
    elif military.functional_type not in {FunctionalType.SEC.value, FunctionalType.SI.value}:
        return "Tipo funcional nao elegivel para AT/PO."

    confirmed = context.confirmed_unavailabilities_for_interval(military.id, service_start, service_end)
    if confirmed:
        return "Existe indisponibilidade confirmada sobreposta ao intervalo."
    restriction_reason = context.restriction_block_reason(military.id, service_start, service_end)
    if restriction_reason:
        return restriction_reason
    planned = context.planned_unavailability_for_interval(military.id, service_start, service_end)
    if planned is not None:
        return f"Indisponibilidade planeada {planned.code}."
    rest_gap = minimum_rest_gap(context, military.id, service_start, service_end)
    if rest_gap is not None and rest_gap < timedelta(hours=MINIMUM_REST_HOURS):
        return "Descanso inferior a oito horas."
    return None


def build_metrics(context: GenerationContext, military: Military, assignment_date: date, service_code: str) -> CandidateMetrics:
    assignments = [
        item
        for item in context.historical_assignments + context.planned_assignments
        if item.military_id == military.id and item.is_visible and item.code in GENERATION_SERVICE_CODES
    ]
    current_team = context.team_for_military_on_date(military.id, assignment_date)
    team_id = current_team.id if current_team else 0
    return CandidateMetrics(
        specific_count=sum(1 for item in assignments if item.code == service_code),
        total_at_po_count=len(assignments),
        night_count=sum(1 for item in assignments if item.code in NIGHT_SERVICE_CODES),
        weekend_count=sum(1 for item in assignments if item.assignment_date.weekday() >= 5),
        consecutive_count=consecutive_count(assignments, assignment_date),
        team_load=context.team_load.get((assignment_date, service_code, team_id), 0),
        days_since_equivalent=days_since_equivalent(assignments, assignment_date, service_code),
        stable_id=military.id,
    )


def consecutive_count(assignments: list[Assignment], assignment_date: date) -> int:
    dates = {item.assignment_date for item in assignments}
    count = 0
    current = assignment_date - timedelta(days=1)
    while current in dates:
        count += 1
        current -= timedelta(days=1)
    return count


def days_since_equivalent(assignments: list[Assignment], assignment_date: date, service_code: str) -> int:
    previous_dates = [item.assignment_date for item in assignments if item.code == service_code and item.assignment_date < assignment_date]
    if not previous_dates:
        return 9999
    return (assignment_date - max(previous_dates)).days


def minimum_rest_gap(
    context: GenerationContext,
    military_id: int,
    service_start: datetime,
    service_end: datetime,
) -> timedelta | None:
    gaps = []
    for assignment in context.all_current_assignments:
        if assignment.military_id != military_id or assignment.code not in SERVICE_TIME_WINDOWS:
            continue
        existing_start, existing_end = service_interval(assignment.assignment_date, assignment.code)
        if existing_start <= service_start:
            gaps.append(service_start - existing_end)
        else:
            gaps.append(existing_start - service_end)
    if not gaps:
        return None
    return min(gaps)


def service_interval(assignment_date: date, service_code: str) -> tuple[datetime, datetime]:
    window = SERVICE_TIME_WINDOWS[service_code]
    start = datetime.combine(assignment_date, window.start_time)
    end_date = assignment_date + timedelta(days=1) if window.crosses_midnight else assignment_date
    return start, datetime.combine(end_date, window.end_time)


def planned_unavailability_overlap(military_id: int, service_start: datetime, service_end: datetime) -> Unavailability | None:
    candidates = (
        Unavailability.query.filter(
            Unavailability.military_id == military_id,
            Unavailability.is_active.is_(True),
            Unavailability.status == UnavailabilityStatus.PLANNED.value,
            Unavailability.start_date <= service_end.date(),
            Unavailability.end_date >= service_start.date() - timedelta(days=1),
        )
        .order_by(Unavailability.start_date.asc(), Unavailability.id.asc())
        .all()
    )
    for unavailability in candidates:
        interval = interval_for_unavailability(unavailability)
        if overlaps(interval.effective_start, interval.effective_end, service_start, service_end):
            return unavailability
    return None


def persist_system_assignment(context: GenerationContext, military: Military, assignment_date: date, service_code: str) -> Assignment:
    assignment = next(
        item
        for item in context.planned_assignments
        if item.military_id == military.id and item.assignment_date == assignment_date and item.code == service_code
    )
    db.session.add(assignment)
    db.session.flush()
    db.session.add(
        AssignmentChange(
            assignment=assignment,
            change_type=AssignmentChangeType.CREATED.value,
            previous_code=None,
            new_code=service_code,
            previous_locked=None,
            new_locked=False,
            previous_override=None,
            new_override=False,
            reason="Geracao automatica inicial AT/PO.",
        )
    )
    team = context.team_for_military_on_date(military.id, assignment_date)
    if team:
        key = (assignment_date, service_code, team.id)
        context.team_load[key] = context.team_load.get(key, 0) + 1
    return assignment


def persist_selection_details(run: GenerationRun, selection: SelectionResult) -> None:
    for decision in selection.eligible + selection.excluded:
        db.session.add(selection_detail(run, selection.assignment_date, selection.service_code, decision))
    for selected in selection.selected:
        db.session.add(selection_detail(run, selection.assignment_date, selection.service_code, selected))
    if selection.unfilled_count:
        add_no_candidate_detail(
            run,
            selection.assignment_date,
            selection.service_code,
            f"Cobertura incompleta: faltam {selection.unfilled_count}.",
        )


def selection_detail(
    run: GenerationRun,
    assignment_date: date,
    service_code: str,
    decision: CandidateDecision,
) -> AssignmentSelectionDetail:
    return AssignmentSelectionDetail(
        generation_run=run,
        assignment_date=assignment_date,
        service_code=service_code,
        military_id=decision.military.id,
        is_eligible=decision.is_eligible,
        is_selected=decision.is_selected,
        reason=decision.reason,
        position=decision.position,
        metrics_json=json.dumps(decision.metrics.as_dict(), sort_keys=True) if decision.metrics else None,
    )


def add_no_candidate_detail(run: GenerationRun, assignment_date: date, service_code: str, reason: str) -> None:
    db.session.add(
        AssignmentSelectionDetail(
            generation_run=run,
            assignment_date=assignment_date,
            service_code=service_code,
            military_id=None,
            is_eligible=False,
            is_selected=False,
            reason=reason,
            position=None,
            metrics_json=None,
        )
    )


def iter_month_dates(month_start: date, month_end: date):
    current = month_start
    while current <= month_end:
        yield current
        current += timedelta(days=1)


def first_day_months_before(month_start: date, months: int) -> date:
    year = month_start.year
    month = month_start.month
    for _ in range(months):
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return date(year, month, 1)


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


def latest_generation_run(schedule_version_id: int) -> GenerationRun | None:
    return (
        GenerationRun.query.filter_by(schedule_version_id=schedule_version_id)
        .order_by(GenerationRun.created_at.desc(), GenerationRun.id.desc())
        .first()
    )
