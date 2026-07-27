from dataclasses import dataclass
from datetime import date

from werkzeug.datastructures import MultiDict


MAX_REASON_LENGTH = 500


@dataclass(frozen=True)
class MembershipValidationResult:
    data: dict
    errors: dict[str, str]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def validate_membership_payload(
    form_data: MultiDict | dict,
    *,
    require_team: bool = True,
    require_start_date: bool = True,
    allow_end_date: bool = False,
) -> MembershipValidationResult:
    team_id_value, team_id_error = _parse_team_id(form_data.get("team_id", ""))
    start_date_value, start_date_error = _parse_date(
        form_data.get("start_date", ""),
        required=require_start_date,
        field_name="data de inicio",
    )
    end_date_value, end_date_error = _parse_date(
        form_data.get("end_date", ""),
        required=False,
        field_name="data de fim",
    )
    reason = _clean_text(form_data.get("reason", ""))

    errors: dict[str, str] = {}
    if require_team and team_id_error:
        errors["team_id"] = team_id_error
    if start_date_error:
        errors["start_date"] = start_date_error
    if allow_end_date and end_date_error:
        errors["end_date"] = end_date_error
    if allow_end_date and start_date_value and end_date_value and end_date_value < start_date_value:
        errors["end_date"] = "A data de fim nao pode ser anterior a data de inicio."
    if len(reason) > MAX_REASON_LENGTH:
        errors["reason"] = f"O motivo nao pode exceder {MAX_REASON_LENGTH} caracteres."

    return MembershipValidationResult(
        data={
            "team_id": team_id_value,
            "start_date": start_date_value,
            "end_date": end_date_value if allow_end_date else None,
            "reason": reason or None,
        },
        errors=errors,
    )


def _clean_text(value) -> str:
    return str(value or "").strip()


def _parse_team_id(value) -> tuple[int | None, str | None]:
    cleaned = _clean_text(value)
    if not cleaned:
        return None, "Selecione uma equipa."
    try:
        return int(cleaned), None
    except ValueError:
        return None, "Selecione uma equipa valida."


def _parse_date(
    value,
    *,
    required: bool,
    field_name: str,
) -> tuple[date | None, str | None]:
    cleaned = _clean_text(value)
    if not cleaned:
        if required:
            return None, f"A {field_name} e obrigatoria."
        return None, None

    try:
        return date.fromisoformat(cleaned), None
    except ValueError:
        return None, "Introduza uma data valida."
