from dataclasses import dataclass
from datetime import date, datetime, time

from werkzeug.datastructures import MultiDict

from app.models import ALLOWED_RESTRICTION_TYPES, WEEKDAY_FIELDS


MAX_REASON_LENGTH = 500
MAX_NOTES_LENGTH = 2000


@dataclass(frozen=True)
class RestrictionValidationResult:
    data: dict
    errors: dict[str, str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_restriction_payload(form_data: MultiDict | dict) -> RestrictionValidationResult:
    restriction_type = _clean_text(form_data.get("restriction_type", ""))
    start_date, start_date_error = _parse_date(
        form_data.get("start_date", ""),
        "A data inicial é obrigatória.",
    )
    end_date, end_date_error = _parse_optional_date(form_data.get("end_date", ""))
    is_full_day = _parse_checkbox(form_data.get("is_full_day"))
    start_time, start_time_error = _parse_optional_time(form_data.get("start_time", ""))
    end_time, end_time_error = _parse_optional_time(form_data.get("end_time", ""))
    reason = _clean_text(form_data.get("reason", ""))
    notes = _clean_text(form_data.get("notes", ""))
    weekdays = {field: _parse_checkbox(form_data.get(field)) for field in WEEKDAY_FIELDS}
    is_active = _parse_checkbox(form_data.get("is_active", "1"))

    errors: dict[str, str] = {}
    if restriction_type not in ALLOWED_RESTRICTION_TYPES:
        errors["restriction_type"] = "Selecione um tipo de restrição válido."
    if start_date_error:
        errors["start_date"] = start_date_error
    if end_date_error:
        errors["end_date"] = end_date_error
    if start_date and end_date and end_date < start_date:
        errors["end_date"] = "A data final não pode ser anterior à data inicial."
    if start_time_error:
        errors["start_time"] = start_time_error
    if end_time_error:
        errors["end_time"] = end_time_error

    if is_full_day:
        start_time = None
        end_time = None
    elif (start_time is None) != (end_time is None):
        errors["start_time"] = "Preencha a hora inicial e a hora final, ou marque dia completo."
    elif start_time is None and end_time is None:
        errors["is_full_day"] = "Marque dia completo ou preencha um intervalo horário."

    if not reason:
        errors["reason"] = "O motivo é obrigatório."
    elif len(reason) > MAX_REASON_LENGTH:
        errors["reason"] = f"O motivo não pode exceder {MAX_REASON_LENGTH} caracteres."
    if len(notes) > MAX_NOTES_LENGTH:
        errors["notes"] = f"As notas não podem exceder {MAX_NOTES_LENGTH} caracteres."

    return RestrictionValidationResult(
        data={
            "restriction_type": restriction_type,
            "start_date": start_date,
            "end_date": end_date,
            "start_time": start_time,
            "end_time": end_time,
            "reason": reason,
            "notes": notes or None,
            "is_active": is_active,
            **weekdays,
        },
        errors=errors,
    )


def validate_restriction_test_payload(form_data: MultiDict | dict) -> RestrictionValidationResult:
    service_date, service_date_error = _parse_date(
        form_data.get("service_date", ""),
        "A data do serviço é obrigatória.",
    )
    start_time, start_time_error = _parse_optional_time(form_data.get("start_time", ""))
    end_time, end_time_error = _parse_optional_time(form_data.get("end_time", ""))
    description = _clean_text(form_data.get("description", ""))

    errors: dict[str, str] = {}
    if service_date_error:
        errors["service_date"] = service_date_error
    if start_time_error:
        errors["start_time"] = start_time_error
    if end_time_error:
        errors["end_time"] = end_time_error
    if start_time is None:
        errors["start_time"] = "A hora inicial é obrigatória."
    if end_time is None:
        errors["end_time"] = "A hora final é obrigatória."

    service_start = service_end = None
    if service_date and start_time and end_time:
        service_start = datetime.combine(service_date, start_time)
        service_end_date = service_date if end_time > start_time else date.fromordinal(service_date.toordinal() + 1)
        service_end = datetime.combine(service_end_date, end_time)

    return RestrictionValidationResult(
        data={
            "service_date": service_date,
            "start_time": start_time,
            "end_time": end_time,
            "service_start": service_start,
            "service_end": service_end,
            "description": description,
        },
        errors=errors,
    )


def _clean_text(value) -> str:
    return str(value or "").strip()


def _parse_checkbox(value) -> bool:
    return value in {"1", "true", "True", "on", "yes", "sim"}


def _parse_date(value, required_message: str) -> tuple[date | None, str | None]:
    cleaned = _clean_text(value)
    if not cleaned:
        return None, required_message
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
