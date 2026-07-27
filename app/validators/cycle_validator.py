from dataclasses import dataclass
from datetime import date, timedelta

from werkzeug.datastructures import MultiDict

from app.services.cycle_calculator import MAX_PREVIEW_DAYS, VALID_PHASES


MAX_NOTES_LENGTH = 1000


@dataclass(frozen=True)
class CycleReferenceValidationResult:
    data: dict
    errors: dict[str, str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_cycle_reference_payload(form_data: MultiDict | dict) -> CycleReferenceValidationResult:
    reference_date, reference_date_error = _parse_date(
        form_data.get("reference_date", ""),
        "A data de referência é obrigatória.",
    )
    valid_from, valid_from_error = _parse_date(
        form_data.get("valid_from", ""),
        "A data de início de validade é obrigatória.",
    )
    phase, phase_error = _parse_phase(form_data.get("reference_phase", ""))
    notes = _clean_text(form_data.get("notes", ""))

    errors: dict[str, str] = {}
    if reference_date_error:
        errors["reference_date"] = reference_date_error
    if valid_from_error:
        errors["valid_from"] = valid_from_error
    if phase_error:
        errors["reference_phase"] = phase_error
    if len(notes) > MAX_NOTES_LENGTH:
        errors["notes"] = f"As observações não podem exceder {MAX_NOTES_LENGTH} caracteres."

    return CycleReferenceValidationResult(
        data={
            "reference_date": reference_date,
            "reference_phase": phase,
            "valid_from": valid_from,
            "notes": notes or None,
        },
        errors=errors,
    )


def validate_preview_payload(form_data: MultiDict | dict) -> CycleReferenceValidationResult:
    team_id, team_id_error = _parse_team_id(form_data.get("team_id", ""))
    today = date.today()
    start_date, start_error = _parse_date(
        form_data.get("start_date", today.isoformat()),
        "A data inicial é obrigatória.",
    )
    end_default = (start_date + timedelta(days=13)).isoformat() if start_date else ""
    end_date, end_error = _parse_date(
        form_data.get("end_date", end_default),
        "A data final é obrigatória.",
    )

    errors: dict[str, str] = {}
    if team_id_error:
        errors["team_id"] = team_id_error
    if start_error:
        errors["start_date"] = start_error
    if end_error:
        errors["end_date"] = end_error
    if start_date and end_date:
        if end_date < start_date:
            errors["end_date"] = "A data final não pode ser anterior à data inicial."
        elif (end_date - start_date).days + 1 > MAX_PREVIEW_DAYS:
            errors["end_date"] = f"O intervalo não pode exceder {MAX_PREVIEW_DAYS} dias."

    return CycleReferenceValidationResult(
        data={
            "team_id": team_id,
            "start_date": start_date,
            "end_date": end_date,
        },
        errors=errors,
    )


def _clean_text(value) -> str:
    return str(value or "").strip()


def _parse_phase(value) -> tuple[int | None, str | None]:
    cleaned = _clean_text(value)
    if not cleaned:
        return None, "A fase é obrigatória."
    try:
        phase = int(cleaned)
    except ValueError:
        return None, "A fase deve ser um número entre 1 e 6."
    if phase not in VALID_PHASES:
        return None, "A fase deve estar entre 1 e 6."
    return phase, None


def _parse_team_id(value) -> tuple[int | None, str | None]:
    cleaned = _clean_text(value)
    if not cleaned:
        return None, "Selecione uma equipa."
    try:
        return int(cleaned), None
    except ValueError:
        return None, "Selecione uma equipa válida."


def _parse_date(value, required_message: str) -> tuple[date | None, str | None]:
    cleaned = _clean_text(value)
    if not cleaned:
        return None, required_message
    try:
        return date.fromisoformat(cleaned), None
    except ValueError:
        return None, "Introduza uma data válida."
