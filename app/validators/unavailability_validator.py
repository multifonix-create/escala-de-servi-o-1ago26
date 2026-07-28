from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from werkzeug.datastructures import MultiDict

from app.models import (
    ALLOWED_COMPENSATION_STATUSES,
    ALLOWED_UNAVAILABILITY_CODES,
    ALLOWED_UNAVAILABILITY_STATUSES,
    CompensationStatus,
    UnavailabilityStatus,
)


MAX_REASON_LENGTH = 500
MAX_LOCATION_LENGTH = 250
MAX_NOTES_LENGTH = 2000
MAX_TRAVEL_MINUTES = 1440


@dataclass(frozen=True)
class UnavailabilityValidationResult:
    data: dict
    errors: dict[str, str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_unavailability_payload(form_data: MultiDict | dict) -> UnavailabilityValidationResult:
    code = _clean_text(form_data.get("code", ""))
    status = _clean_text(form_data.get("status", UnavailabilityStatus.PLANNED.value))
    compensation_status = _clean_text(
        form_data.get("compensation_status", CompensationStatus.NOT_APPLICABLE.value)
    )
    reason = _clean_text(form_data.get("reason", ""))
    location = _clean_text(form_data.get("location", ""))
    compensation_notes = _clean_text(form_data.get("compensation_notes", ""))
    is_full_day = _parse_checkbox(form_data.get("is_full_day"))
    start_date, start_date_error = _parse_date(form_data.get("start_date", ""))
    end_date, end_date_error = _parse_optional_date(form_data.get("end_date", ""))
    start_time, start_time_error = _parse_optional_time(form_data.get("start_time", ""))
    end_time, end_time_error = _parse_optional_time(form_data.get("end_time", ""))
    before, before_error = _parse_travel(form_data.get("travel_minutes_before", "0"))
    after, after_error = _parse_travel(form_data.get("travel_minutes_after", "0"))

    errors: dict[str, str] = {}
    if code not in ALLOWED_UNAVAILABILITY_CODES:
        errors["code"] = "Selecione um código válido."
    if status not in ALLOWED_UNAVAILABILITY_STATUSES:
        errors["status"] = "Selecione um estado válido."
    if compensation_status not in ALLOWED_COMPENSATION_STATUSES:
        errors["compensation_status"] = "Selecione um estado de compensação válido."
    if start_date_error:
        errors["start_date"] = start_date_error
    if end_date_error:
        errors["end_date"] = end_date_error
    if start_time_error:
        errors["start_time"] = start_time_error
    if end_time_error:
        errors["end_time"] = end_time_error
    if before_error:
        errors["travel_minutes_before"] = before_error
    if after_error:
        errors["travel_minutes_after"] = after_error
    if not reason:
        errors["reason"] = "O motivo é obrigatório."
    elif len(reason) > MAX_REASON_LENGTH:
        errors["reason"] = f"O motivo não pode exceder {MAX_REASON_LENGTH} caracteres."
    if len(location) > MAX_LOCATION_LENGTH:
        errors["location"] = f"O local não pode exceder {MAX_LOCATION_LENGTH} caracteres."
    if len(compensation_notes) > MAX_NOTES_LENGTH:
        errors["compensation_notes"] = f"As notas não podem exceder {MAX_NOTES_LENGTH} caracteres."

    if start_date is not None and end_date is None:
        end_date = start_date
    if start_date is not None and end_date is not None and end_date < start_date:
        errors["end_date"] = "A data final não pode ser anterior à inicial."

    if is_full_day:
        start_time = None
        end_time = None
    elif start_time is None or end_time is None:
        errors["start_time"] = "Indique hora inicial e hora final para intervalo parcial."
    elif start_date is not None and end_date is not None:
        interval_start, interval_end = _combine_interval(start_date, end_date, start_time, end_time)
        if interval_end <= interval_start:
            errors["end_time"] = "O intervalo deve terminar depois do início."

    return UnavailabilityValidationResult(
        data={
            "code": code,
            "start_date": start_date,
            "end_date": end_date,
            "start_time": start_time,
            "end_time": end_time,
            "is_full_day": is_full_day,
            "status": status,
            "reason": reason,
            "location": location or None,
            "travel_minutes_before": before or 0,
            "travel_minutes_after": after or 0,
            "compensation_status": compensation_status,
            "compensation_notes": compensation_notes or None,
            "is_active": True,
        },
        errors=errors,
    )


def validate_availability_test_payload(form_data: MultiDict | dict) -> UnavailabilityValidationResult:
    start_date, start_date_error = _parse_date(form_data.get("start_date", ""))
    end_date, end_date_error = _parse_date(form_data.get("end_date", ""))
    start_time, start_time_error = _parse_optional_time(form_data.get("start_time", ""))
    end_time, end_time_error = _parse_optional_time(form_data.get("end_time", ""))
    description = _clean_text(form_data.get("description", ""))
    errors: dict[str, str] = {}
    if start_date_error:
        errors["start_date"] = start_date_error
    if end_date_error:
        errors["end_date"] = end_date_error
    if start_time_error or start_time is None:
        errors["start_time"] = start_time_error or "A hora inicial é obrigatória."
    if end_time_error or end_time is None:
        errors["end_time"] = end_time_error or "A hora final é obrigatória."
    service_start = service_end = None
    if not errors:
        service_start = datetime.combine(start_date, start_time)
        service_end = datetime.combine(end_date, end_time)
        if service_end <= service_start:
            errors["end_time"] = "O fim deve ser posterior ao início."
    return UnavailabilityValidationResult(
        data={
            "service_start": service_start,
            "service_end": service_end,
            "description": description,
        },
        errors=errors,
    )


def _combine_interval(start_date: date, end_date: date, start_time: time, end_time: time) -> tuple[datetime, datetime]:
    interval_start = datetime.combine(start_date, start_time)
    adjusted_end_date = end_date
    if end_date == start_date and end_time <= start_time:
        adjusted_end_date = end_date + timedelta(days=1)
    return interval_start, datetime.combine(adjusted_end_date, end_time)


def _clean_text(value) -> str:
    return str(value or "").strip()


def _parse_checkbox(value) -> bool:
    return value in {"1", "true", "True", "on", "yes", "sim"}


def _parse_date(value) -> tuple[date | None, str | None]:
    cleaned = _clean_text(value)
    if not cleaned:
        return None, "A data é obrigatória."
    try:
        return date.fromisoformat(cleaned), None
    except ValueError:
        return None, "Introduza uma data válida."


def _parse_optional_date(value) -> tuple[date | None, str | None]:
    cleaned = _clean_text(value)
    if not cleaned:
        return None, None
    try:
        return date.fromisoformat(cleaned), None
    except ValueError:
        return None, "Introduza uma data válida."


def _parse_optional_time(value) -> tuple[time | None, str | None]:
    cleaned = _clean_text(value)
    if not cleaned:
        return None, None
    try:
        return time.fromisoformat(cleaned), None
    except ValueError:
        return None, "Introduza uma hora válida."


def _parse_travel(value) -> tuple[int | None, str | None]:
    cleaned = _clean_text(value) or "0"
    try:
        parsed = int(cleaned)
    except ValueError:
        return None, "Indique um número inteiro."
    if parsed < 0:
        return None, "O valor não pode ser negativo."
    if parsed > MAX_TRAVEL_MINUTES:
        return None, f"O valor não pode exceder {MAX_TRAVEL_MINUTES} minutos."
    return parsed, None
