from dataclasses import dataclass
from datetime import date
import re

from werkzeug.datastructures import MultiDict

from app.models import FunctionalType
from app.models.military import build_full_name


MAX_FIRST_NAME_LENGTH = 90
MAX_LAST_NAME_LENGTH = 120
MAX_NIM_LENGTH = 30
MAX_PHONE_LENGTH = 20
MAX_NOTES_LENGTH = 2000
ALLOWED_FUNCTIONAL_TYPES = tuple(item.value for item in FunctionalType)
NIM_PATTERN = re.compile(r"^\d{1,30}$")
PHONE_PATTERN = re.compile(r"^(?:\+351)?[239]\d{8}$")


@dataclass(frozen=True)
class MilitaryValidationResult:
    data: dict
    errors: dict[str, str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_military_payload(form_data: MultiDict | dict) -> MilitaryValidationResult:
    first_name = _clean_text(form_data.get("first_name", ""))
    last_name = _clean_text(form_data.get("last_name", ""))
    legacy_name = _clean_text(form_data.get("name", ""))
    if legacy_name and not first_name and not last_name:
        first_name, _, last_name = legacy_name.partition(" ")
        last_name = last_name.strip()
    nim = _clean_text(form_data.get("nim", ""))
    phone_number_raw = _clean_text(form_data.get("phone_number", ""))
    functional_type = _clean_text(form_data.get("functional_type", ""))
    team_id = _clean_text(form_data.get("team_id", ""))
    team_field_present = "team_id" in form_data
    notes = _clean_text(form_data.get("notes", ""))
    is_active = _parse_checkbox(form_data.get("is_active"))
    is_paid_service_volunteer = _parse_checkbox(form_data.get("is_paid_service_volunteer"))
    start_date_value, start_date_error = _parse_date(form_data.get("start_date", ""))
    end_date_value, end_date_error = _parse_optional_date(form_data.get("end_date", ""))
    phone_number, phone_error = normalize_phone_number(phone_number_raw)

    errors: dict[str, str] = {}

    if not first_name:
        errors["first_name"] = "O nome é obrigatório."
    elif len(first_name) > MAX_FIRST_NAME_LENGTH:
        errors["first_name"] = f"O nome não pode exceder {MAX_FIRST_NAME_LENGTH} caracteres."

    if not last_name:
        errors["last_name"] = "O sobrenome é obrigatório."
    elif len(last_name) > MAX_LAST_NAME_LENGTH:
        errors["last_name"] = f"O sobrenome não pode exceder {MAX_LAST_NAME_LENGTH} caracteres."

    if not nim:
        errors["nim"] = "O NIM é obrigatório."
    elif not NIM_PATTERN.fullmatch(nim):
        errors["nim"] = "O NIM deve conter apenas algarismos e ser guardado como texto."
    elif len(nim) > MAX_NIM_LENGTH:
        errors["nim"] = f"O NIM não pode exceder {MAX_NIM_LENGTH} caracteres."

    if phone_error and "phone_number" in form_data:
        errors["phone_number"] = phone_error

    if functional_type not in ALLOWED_FUNCTIONAL_TYPES:
        errors["functional_type"] = "Selecione um tipo funcional válido."

    if team_field_present and functional_type == FunctionalType.PATRULHEIRO.value and not team_id:
        errors["team_id"] = "Patrulheiro exige equipa operacional A-E."

    if functional_type in {
        FunctionalType.CMD.value,
        FunctionalType.SEC.value,
        FunctionalType.SI.value,
    } and team_id:
        errors["team_id"] = "CMD, SEC e SI não podem ter equipa operacional A-E."

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

    full_name = build_full_name(first_name, last_name)

    data = {
            "name": full_name,
            "first_name": first_name,
            "last_name": last_name,
            "nim": nim,
            "phone_number": phone_number,
            "functional_type": functional_type,
            "is_paid_service_volunteer": is_paid_service_volunteer,
            "is_active": is_active,
            "start_date": start_date_value,
            "end_date": end_date_value,
            "notes": notes or None,
    }
    if team_field_present:
        data["team_id"] = int(team_id) if team_id.isdigit() else None

    return MilitaryValidationResult(
        data=data,
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


def normalize_phone_number(value: str | None) -> tuple[str | None, str | None]:
    cleaned = _clean_text(value).replace(" ", "")
    if not cleaned:
        return None, "O contacto é obrigatório."
    if len(cleaned) > MAX_PHONE_LENGTH:
        return None, f"O contacto não pode exceder {MAX_PHONE_LENGTH} caracteres."
    if not PHONE_PATTERN.fullmatch(cleaned):
        return None, "Introduza um contacto português válido, por exemplo 912345678 ou +351912345678."
    local_number = cleaned[4:] if cleaned.startswith("+351") else cleaned
    return f"+351{local_number}", None
