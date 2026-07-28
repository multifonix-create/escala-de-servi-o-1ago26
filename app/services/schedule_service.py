from datetime import date

from app.extensions import db
from app.models import (
    ScheduleMonth,
    ScheduleMonthStatus,
    ScheduleVersion,
    ScheduleVersionSource,
)
from app.validators.schedule_validator import validate_schedule_month_path


class ScheduleServiceError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__("Dados de escala invalidos.")
        self.errors = errors


def current_month(today: date | None = None) -> tuple[int, int]:
    reference = today or date.today()
    return reference.year, reference.month


def previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


def list_schedule_months() -> list[ScheduleMonth]:
    return (
        ScheduleMonth.query.order_by(
            ScheduleMonth.year.desc(),
            ScheduleMonth.month.desc(),
        ).all()
    )


def get_schedule_month(year: int, month: int) -> ScheduleMonth | None:
    validation = validate_schedule_month_path(year, month)
    if not validation.is_valid:
        raise ScheduleServiceError(validation.errors)
    return ScheduleMonth.query.filter_by(year=year, month=month).one_or_none()


def create_schedule_month(year: int, month: int) -> ScheduleMonth:
    validation = validate_schedule_month_path(year, month)
    if not validation.is_valid:
        raise ScheduleServiceError(validation.errors)

    existing = get_schedule_month(year, month)
    if existing is not None:
        raise ScheduleServiceError({"month": "Este mes de escala ja existe."})

    schedule_month = ScheduleMonth(
        year=year,
        month=month,
        status=ScheduleMonthStatus.DRAFT.value,
    )
    initial_version = ScheduleVersion(
        schedule_month=schedule_month,
        version_number=1,
        status=ScheduleMonthStatus.DRAFT.value,
        source=ScheduleVersionSource.INITIAL.value,
        description="Versao inicial criada para consulta mensal.",
    )
    try:
        db.session.add(schedule_month)
        db.session.add(initial_version)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return schedule_month


def list_versions(schedule_month_id: int) -> list[ScheduleVersion]:
    return (
        ScheduleVersion.query.filter_by(schedule_month_id=schedule_month_id)
        .order_by(ScheduleVersion.version_number.desc(), ScheduleVersion.id.desc())
        .all()
    )


def get_version_for_month_or_404(schedule_month: ScheduleMonth, version_id: int) -> ScheduleVersion:
    return (
        ScheduleVersion.query.filter_by(
            id=version_id,
            schedule_month_id=schedule_month.id,
        )
        .one_or_404()
    )
