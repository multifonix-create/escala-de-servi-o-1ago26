from calendar import monthrange
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from sqlalchemy import or_

from app.models import (
    CompensationStatus,
    FunctionalType,
    Military,
    ScheduleMonth,
    ScheduleVersion,
    Unavailability,
    UnavailabilityStatus,
)
from app.services import cycle_calculator, membership_service, restriction_service
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

    rows = [
        _build_row(military, days, month_start, month_end, warnings)
        for military in militaries
    ]
    rows.sort(key=_row_sort_key)
    return MonthlyGrid(
        schedule_month=schedule_month,
        version=version or schedule_month.latest_version,
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
) -> MonthlyGridRow:
    group_label = _group_label_for_military(military, month_start, month_end)
    cells = [
        _build_cell(military, grid_day, global_warnings)
        for grid_day in days
    ]
    return MonthlyGridRow(military=military, group_label=group_label, cells=cells)


def _build_cell(
    military: Military,
    grid_day: MonthlyGridDay,
    global_warnings: list[str],
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

    team = membership_service.get_team_for_military_on_date(military.id, current)
    if team is not None:
        cell.team_code = team.code

    if military.functional_type == FunctionalType.PATRULHEIRO.value:
        _apply_cycle(cell, military, team, current, global_warnings)

    _apply_unavailability(cell, military, current)
    _apply_restrictions(cell, military, current)
    return cell


def _apply_cycle(
    cell: MonthlyGridCell,
    military: Military,
    team,
    current: date,
    global_warnings: list[str],
) -> None:
    if team is None:
        message = f"{military.name} sem equipa valida em {current.isoformat()}."
        cell.warnings.append(message)
        global_warnings.append(message)
        return
    try:
        cycle_day = cycle_calculator.calculate_team_day(team, current)
    except cycle_calculator.MissingTeamReferenceError:
        message = f"Equipa {team.code} sem referencia de ciclo valida em {current.isoformat()}."
        cell.warnings.append(message)
        global_warnings.append(message)
        return
    cell.cycle_code = cycle_day.code
    cell.cycle_phase = cycle_day.phase
    if cycle_day.code in {"DS", "DC"}:
        cell.primary_code = cycle_day.code


def _apply_unavailability(cell: MonthlyGridCell, military: Military, current: date) -> None:
    day_start = datetime.combine(current, time.min)
    day_end = day_start + timedelta(days=1)
    matches = []
    for unavailability in _unavailabilities_for_day(military.id, current):
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


def _apply_restrictions(cell: MonthlyGridCell, military: Military, current: date) -> None:
    restrictions = [
        restriction
        for restriction in restriction_service.get_active_restrictions_for_military_on_date(military.id, current)
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


def _group_label_for_military(military: Military, month_start: date, month_end: date) -> str:
    if military.functional_type in GROUP_ORDER:
        return military.functional_type
    current = month_start
    while current <= month_end:
        team = membership_service.get_team_for_military_on_date(military.id, current)
        if team is not None:
            return f"Equipa {team.code}"
        current += timedelta(days=1)
    return "Patrulheiros sem equipa"


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
    return sorted(legend)


def _unique(values: list[str]) -> list[str]:
    seen = set()
    unique_values = []
    for value in values:
        if value not in seen:
            seen.add(value)
            unique_values.append(value)
    return unique_values
