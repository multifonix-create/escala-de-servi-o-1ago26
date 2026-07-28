from dataclasses import dataclass


MIN_SCHEDULE_YEAR = 2000
MAX_SCHEDULE_YEAR = 2100


@dataclass(frozen=True)
class ScheduleMonthValidationResult:
    year: int | None
    month: int | None
    errors: dict[str, str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_schedule_month_payload(data: dict) -> ScheduleMonthValidationResult:
    errors: dict[str, str] = {}
    year = _parse_int(data.get("year"), "year", "Indique um ano valido.", errors)
    month = _parse_int(data.get("month"), "month", "Indique um mes valido.", errors)

    if year is not None and not MIN_SCHEDULE_YEAR <= year <= MAX_SCHEDULE_YEAR:
        errors["year"] = f"O ano deve estar entre {MIN_SCHEDULE_YEAR} e {MAX_SCHEDULE_YEAR}."
    if month is not None and not 1 <= month <= 12:
        errors["month"] = "O mes deve estar entre 1 e 12."

    return ScheduleMonthValidationResult(year=year, month=month, errors=errors)


def validate_schedule_month_path(year: int, month: int) -> ScheduleMonthValidationResult:
    return validate_schedule_month_payload({"year": year, "month": month})


def _parse_int(value, field: str, message: str, errors: dict[str, str]) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        errors[field] = message
        return None
