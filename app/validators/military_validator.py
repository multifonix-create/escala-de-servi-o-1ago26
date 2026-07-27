from dataclasses import dataclass
from datetime import date

from werkzeug.datastructures import MultiDict

from app.models import FunctionalType


MAX_NAME_LENGTH = 180
MAX_NIM_LENGTH = 30
MAX_NOTES_LENGTH = 2000
ALLOWED_FUNCTIONAL_TYPES = tuple(item.value for item in FunctionalType)


@dataclass(frozen=True)
class MilitaryValidationResult:
    data: dict
    errors: dict[str, str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_military_payload(form_data: MultiDict | dict) -> MilitaryValidationResult:
    name = _clean_text(form_data.get("name", ""))
    nim = _clean_text(form_data.get("nim", ""))
    functional_type = _clean_text(form_data.get("functional_type", ""))
    notes = _clean_text(form_data.get("notes", ""))
    is_active = _parse_checkbox(form_data.get("is_active"))
    start_date_value, start_date_error = _parse_date(form_data.get("start_date", ""))
    end_date_value, end_date_error = _parse_optional_date(form_data.get("end_date", ""))

    errors: dict[str, str] = {}

    if not name:
        errors["name"] = "O nome é obrigatório."
    elif len(name) > MAX_NAME_LENGTH:
        errors["name"] = f"O nome não pode exceder {MAX_NAME_LENGTH} caracteres."

    if not nim:
        errors["nim"] = "O NIM é obrigatório."
    elif len(nim) > MAX_NIM_LENGTH:
        errors["nim"] = f"O NIM não pode exceder {MAX_NIM_LENGTH} caracteres."

    if functional_type not in ALLOWED_FUNCTIONAL_TYPES:
        errors["functional_type"] = "Selecione um tipo funcional válido."

    if start_date_error:
        errors["start_date"] = start_date_error

    if end_date_error:
        errors["end_date"] = end_date_error

    if (
        start_date_value is not None
        and end_date_value is not None
        and end_date_value < start_date_value
    ):
        errors["end_date"] = "A data de fim não pode ser anterior à data de início."

    if len(notes) > MAX_NOTES_LENGTH:
        errors["notes"] = f"As notas não podem exceder {MAX_NOTES_LENGTH} caracteres."

    return MilitaryValidationResult(
        data={
            "name": name,
            "nim": nim,
            "functional_type": functional_type,
            "is_active": is_active,
            "start_date": start_date_value,
            "end_date": end_date_value,
            "notes": notes or None,
        },
        errors=errors,
    )


def _clean_text(value) -> str:
    return str(value or "").strip()


def _parse_checkbox(value) -> bool:
    return value in {"1", "true", "True", "on", "yes", "sim"}


def _parse_date(value) -> tuple[date | None, str | None]:
    cleaned = _clean_text(value)
    if not cleaned:
        return None, "A data de início é obrigatória."

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
