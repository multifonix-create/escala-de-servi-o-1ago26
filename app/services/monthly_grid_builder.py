from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from sqlalchemy import or_

from app.models import (
    Assignment,
    CompensationStatus,
    FunctionalType,
    Military,
    MilitaryRestriction,
    MilitaryTeamHistory,
    ScheduleMonth,
    ScheduleVersion,
    Team,
    TeamCycleReference,
    Unavailability,
    UnavailabilityStatus,
)
from app.services import cycle_calculator
from app.services.unavailability_evaluator import interval_for_unavailability, overlaps


@dataclass(frozen=True)
class MonthlyGridDay:
    date: date
    day_number: int
    weekday_label: str
    is_weekend: bool
    is_holiday: bool = False


@dataclass
class MonthlyGridCell:
    date: date
    primary_code: str | None = None
    cycle_code: str | None = None
    cycle_phase: int | None = None
    team_code: str | None = None
    unavailability: Unavailability | None = None
    restriction_count: int = 0
    restriction_labels: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    is_weekend: bool = False
    is_holiday: bool = False
    is_outside_period: bool = False
    is_partial_unavailability: bool = False
    assignment: Assignment | None = None
    manual_code: str | None = None
    source: str | None = None
    is_locked: bool = False
    has_override: bool = False
    notes: str | None = None
    history_count: int = 0

    @property
    def css_classes(self) -> str:
        classes = ["schedule-cell"]
        if self.is_weekend:
            classes.append("schedule-cell--weekend")
        if self.is_outside_period:
            classes.append("schedule-cell--outside")
        if self.cycle_code:
            classes.append(f"schedule-cell--cycle-{self.cycle_code.lower()}")
        if self.unavailability:
            classes.append("schedule-cell--unavailability")
            classes.append(f"schedule-cell--{self.unavailability.status.lower()}")
        if self.restriction_count:
            classes.append("schedule-cell--restriction")
        if self.warnings:
            classes.append("schedule-cell--warning")
        if self.assignment and self.assignment.is_visible:
            classes.append("schedule-cell--manual")
        if self.is_locked:
            classes.append("schedule-cell--locked")
        if self.has_override:
            classes.append("schedule-cell--override")
        return " ".join(classes)

    @property
    def tooltip(self) -> str:
        parts = []
        if self.team_code:
            parts.append(f"Equipa {self.team_code}")
        if self.cycle_code:
            parts.append(f"Ciclo: {self.cycle_code}")
        if self.unavailability:
            parts.append(f"Indisponibilidade: {self.unavailability.code} ({self.unavailability.status})")
            if self.is_partial_unavailability:
                parts.append("Parcial")
            if self.unavailability.compensation_status == CompensationStatus.PENDING_DECISION.value:
                parts.append("Compensacao pendente")
        if self.restriction_labels:
            parts.append("Restricoes: " + ", ".join(self.restriction_labels))
        if self.manual_code:
            parts.append(f"Manual: {self.manual_code}")
        if self.is_locked:
            parts.append("Bloqueada")
        if self.has_override:
            parts.append("Override autorizado")
        if self.notes:
            parts.append("Notas: " + self.notes)
        parts.extend(self.warnings)
        return " | ".join(parts)


@dataclass(frozen=True)
class MonthlyGridRow:
    military: Military
    group_label: str
    cells: list[MonthlyGridCell]


@dataclass(frozen=True)
class MonthlyGrid:
    schedule_month: ScheduleMonth
    version: ScheduleVersion | None
    days: list[MonthlyGridDay]
    rows: list[MonthlyGridRow]
    warnings: list[str]
    legend: list[str]


GROUP_ORDER = {
    FunctionalType.CMD.value: 0,
    FunctionalType.SEC.value: 1,
    FunctionalType.SI.value: 2,
}

WEEKDAY_SHORT = ("Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom")


def build_monthly_grid(
    schedule_month: ScheduleMonth,
    version: ScheduleVersion | None = None,
) -> MonthlyGrid:
    days = _build_days(schedule_month.year, schedule_month.month)
    month_start = days[0].date
    month_end = days[-1].date
    militaries = _list_relevant_militaries(month_start, month_end)
    warnings: list[str] = []

    if not militaries:
        warnings.append("Nao existem militares registados para este mes.")

    selected_version = version or schedule_month.latest_version
    assignments = _assignments_by_cell(selected_version) if selected_version else {}
    context = _build_grid_context(militaries, month_start, month_end)

    rows = [
        _build_row(military, days, month_start, month_end, warnings, assignments, context)
        for military in militaries
    ]
    rows.sort(key=_row_sort_key)
    return MonthlyGrid(
        schedule_month=schedule_month,
        version=selected_version,
        days=days,
        rows=rows,
        warnings=_unique(warnings),
        legend=_build_legend(rows),
    )


def _build_days(year: int, month: int) -> list[MonthlyGridDay]:
    total_days = monthrange(year, month)[1]
    days = []
    for day_number in range(1, total_days + 1):
        current = date(year, month, day_number)
        days.append(
            MonthlyGridDay(
                date=current,
                day_number=day_number,
                weekday_label=WEEKDAY_SHORT[current.weekday()],
                is_weekend=current.weekday() >= 5,
            )
        )
    return days


def _list_relevant_militaries(month_start: date, month_end: date) -> list[Military]:
    return (
        Military.query.filter(
            Military.start_date <= month_end,
            or_(Military.end_date.is_(None), Military.end_date >= month_start),
        )
        .order_by(Military.name.asc(), Military.nim.asc())
        .all()
    )


def _build_row(
    military: Military,
    days: list[MonthlyGridDay],
    month_start: date,
    month_end: date,
    global_warnings: list[str],
    assignments: dict[tuple[int, date], Assignment],
    context: dict,
) -> MonthlyGridRow:
    group_label = _group_label_for_military(military, month_start, month_end, context)
    cells = [
        _build_cell(military, grid_day, global_warnings, assignments, context)
        for grid_day in days
    ]
    return MonthlyGridRow(military=military, group_label=group_label, cells=cells)


def _build_cell(
    military: Military,
    grid_day: MonthlyGridDay,
    global_warnings: list[str],
    assignments: dict[tuple[int, date], Assignment],
    context: dict,
) -> MonthlyGridCell:
    current = grid_day.date
    outside_period = current < military.start_date or (
        military.end_date is not None and current > military.end_date
    )
    cell = MonthlyGridCell(
        date=current,
        is_weekend=grid_day.is_weekend,
        is_holiday=grid_day.is_holiday,
        is_outside_period=outside_period,
    )
    if outside_period:
        return cell

    team = _team_for_military_on_date(context, military.id, current)
    if team is not None:
        cell.team_code = team.code

    if military.functional_type == FunctionalType.PATRULHEIRO.value:
        _apply_cycle(cell, military, team, current, global_warnings, context)

    _apply_unavailability(cell, military, current, context)
    _apply_restrictions(cell, military, current, context)
    _apply_assignment(cell, assignments.get((military.id, current)))
    return cell


def _apply_assignment(cell: MonthlyGridCell, assignment: Assignment | None) -> None:
    if assignment is None or not assignment.is_visible:
        return
    cell.assignment = assignment
    cell.manual_code = assignment.code if assignment.is_manual else None
    cell.primary_code = assignment.code
    cell.source = assignment.source
    cell.is_locked = assignment.is_locked
    cell.has_override = assignment.has_override
    cell.notes = assignment.notes
    cell.history_count = len(assignment.changes)


def _apply_cycle(
    cell: MonthlyGridCell,
    military: Military,
    team,
    current: date,
    global_warnings: list[str],
    context: dict,
) -> None:
    if team is None:
        message = f"{military.name} sem equipa valida em {current.isoformat()}."
        cell.warnings.append(message)
        global_warnings.append(message)
        return
    try:
        cycle_day = _cycle_day_for_team(context, team, current)
    except cycle_calculator.MissingTeamReferenceError:
        message = f"Equipa {team.code} sem referencia de ciclo valida em {current.isoformat()}."
        cell.warnings.append(message)
        global_warnings.append(message)
        return
    cell.cycle_code = cycle_day.code
    cell.cycle_phase = cycle_day.phase
    if cycle_day.code in {"DS", "DC"}:
        cell.primary_code = cycle_day.code


def _apply_unavailability(cell: MonthlyGridCell, military: Military, current: date, context: dict) -> None:
    day_start = datetime.combine(current, time.min)
    day_end = day_start + timedelta(days=1)
    matches = []
    for unavailability in context["unavailabilities_by_military"].get(military.id, []):
        interval = interval_for_unavailability(unavailability)
        if overlaps(interval.effective_start, interval.effective_end, day_start, day_end):
            matches.append(unavailability)
    if not matches:
        return
    matches.sort(key=_unavailability_priority)
    selected = matches[0]
    cell.unavailability = selected
    cell.primary_code = selected.code
    start, end = interval_for_unavailability(selected).start, interval_for_unavailability(selected).end
    cell.is_partial_unavailability = start > day_start or end < day_end


def _apply_restrictions(cell: MonthlyGridCell, military: Military, current: date, context: dict) -> None:
    restrictions = [
        restriction
        for restriction in context["restrictions_by_military"].get(military.id, [])
        if restriction.start_date <= current and (restriction.end_date is None or restriction.end_date >= current)
        if restriction.applies_to_weekday(current.weekday())
    ]
    cell.restriction_count = len(restrictions)
    cell.restriction_labels = [restriction.restriction_type for restriction in restrictions]


def _unavailabilities_for_day(military_id: int, current: date) -> list[Unavailability]:
    return (
        Unavailability.query.filter(
            Unavailability.military_id == military_id,
            Unavailability.is_active.is_(True),
            Unavailability.status != UnavailabilityStatus.CANCELLED.value,
            Unavailability.start_date <= current,
            Unavailability.end_date >= current - timedelta(days=1),
        )
        .order_by(Unavailability.start_date.asc(), Unavailability.id.asc())
        .all()
    )


def _unavailability_priority(unavailability: Unavailability) -> tuple[int, date, int]:
    status_priority = 0 if unavailability.status == UnavailabilityStatus.CONFIRMED.value else 1
    return status_priority, unavailability.start_date, unavailability.id


def _group_label_for_military(military: Military, month_start: date, month_end: date, context: dict) -> str:
    if military.functional_type in GROUP_ORDER:
        return military.functional_type
    current = month_start
    while current <= month_end:
        team = _team_for_military_on_date(context, military.id, current)
        if team is not None:
            return f"Equipa {team.code}"
        current += timedelta(days=1)
    return "Patrulheiros sem equipa"


def _build_grid_context(militaries: list[Military], month_start: date, month_end: date) -> dict:
    military_ids = [military.id for military in militaries]
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
    unavailabilities = (
        Unavailability.query.filter(
            Unavailability.military_id.in_(military_ids),
            Unavailability.is_active.is_(True),
            Unavailability.status != UnavailabilityStatus.CANCELLED.value,
            Unavailability.start_date <= month_end,
            Unavailability.end_date >= month_start - timedelta(days=1),
        )
        .order_by(Unavailability.start_date.asc(), Unavailability.id.asc())
        .all()
    ) if military_ids else []
    restrictions = (
        MilitaryRestriction.query.filter(
            MilitaryRestriction.military_id.in_(military_ids),
            MilitaryRestriction.is_active.is_(True),
            MilitaryRestriction.start_date <= month_end,
            or_(MilitaryRestriction.end_date.is_(None), MilitaryRestriction.end_date >= month_start),
        )
        .order_by(MilitaryRestriction.restriction_type.asc(), MilitaryRestriction.id.asc())
        .all()
    ) if military_ids else []
    return {
        "teams_by_id": {team.id: team for team in teams},
        "memberships_by_military": _group_by_military(memberships),
        "references_by_team": _group_by_team(references),
        "unavailabilities_by_military": _group_by_military(unavailabilities),
        "restrictions_by_military": _group_by_military(restrictions),
        "team_date_cache": {},
        "cycle_cache": {},
    }


def _team_for_military_on_date(context: dict, military_id: int, current: date):
    key = (military_id, current)
    if key not in context["team_date_cache"]:
        membership = next(
            (
                item
                for item in context["memberships_by_military"].get(military_id, [])
                if item.start_date <= current and (item.end_date is None or item.end_date >= current)
            ),
            None,
        )
        context["team_date_cache"][key] = context["teams_by_id"].get(membership.team_id) if membership else None
    return context["team_date_cache"][key]


def _cycle_day_for_team(context: dict, team, current: date):
    key = (team.id, current)
    if key in context["cycle_cache"]:
        return context["cycle_cache"][key]
    reference = next(
        (
            item
            for item in context["references_by_team"].get(team.id, [])
            if item.valid_from <= current and (item.valid_until is None or item.valid_until >= current)
        ),
        None,
    )
    if reference is None:
        raise cycle_calculator.MissingTeamReferenceError(
            {"reference": "A equipa nao possui referencia valida para a data indicada."}
        )
    phase = cycle_calculator.calculate_phase(reference.reference_phase, reference.reference_date, current)
    code = cycle_calculator.day_off_code_for_phase(phase, current)
    context["cycle_cache"][key] = cycle_calculator.CycleDay(
        day=current,
        weekday_name=cycle_calculator.WEEKDAY_NAMES[current.weekday()],
        phase=phase,
        code=code,
        explanation=cycle_calculator.explain_calculation(reference, current, phase, code),
    )
    return context["cycle_cache"][key]


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


def _row_sort_key(row: MonthlyGridRow) -> tuple[int, str, str, str]:
    functional_type = row.military.functional_type
    if functional_type in GROUP_ORDER:
        group_order = GROUP_ORDER[functional_type]
    elif row.group_label.startswith("Equipa "):
        group_order = 10 + ord(row.group_label[-1])
    else:
        group_order = 99
    return group_order, row.group_label, row.military.name.lower(), row.military.nim


def _build_legend(rows: list[MonthlyGridRow]) -> list[str]:
    legend = set()
    for row in rows:
        for cell in row.cells:
            if cell.cycle_code in {"DS", "DC"}:
                legend.add(cell.cycle_code)
            if cell.unavailability:
                legend.add(cell.unavailability.code)
                if cell.unavailability.status == UnavailabilityStatus.PLANNED.value:
                    legend.add("Planeada")
                if cell.unavailability.compensation_status == CompensationStatus.PENDING_DECISION.value:
                    legend.add("Compensacao pendente")
            if cell.restriction_count:
                legend.add("Restricao")
            if cell.manual_code:
                legend.add("Manual")
            if cell.is_locked:
                legend.add("Bloqueada")
            if cell.has_override:
                legend.add("Override")
    return sorted(legend)


def _assignments_by_cell(version: ScheduleVersion) -> dict[tuple[int, date], Assignment]:
    assignments = (
        Assignment.query.filter_by(schedule_version_id=version.id)
        .order_by(Assignment.assignment_date.asc(), Assignment.id.asc())
        .all()
    )
    return {
        (assignment.military_id, assignment.assignment_date): assignment
        for assignment in assignments
    }


def _unique(values: list[str]) -> list[str]:
    seen = set()
    unique_values = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)
    return unique_values
