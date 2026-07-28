from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.models import FunctionalType
from app.services import military_service, team_service, unavailability_service
from app.services.military_service import MilitaryServiceError
from app.validators import validate_military_payload


militaries_bp = Blueprint("militaries", __name__, url_prefix="/militares")


@militaries_bp.get("")
def list_militaries():
    status = request.args.get("status", "").strip()
    functional_type = request.args.get("functional_type", "").strip()
    query = request.args.get("q", "").strip()
    team_filter = request.args.get("team", "").strip()

    valid_status = status if status in {"active", "inactive"} else None
    valid_functional_type = (
        functional_type
        if functional_type in {item.value for item in FunctionalType}
        else None
    )

    valid_team_id = None
    without_team = team_filter == "none"
    if team_filter.isdigit():
        valid_team_id = int(team_filter)

    militaries = military_service.list_militaries(
        status=valid_status,
        functional_type=valid_functional_type,
        query=query or None,
        team_id=valid_team_id,
        without_team=without_team,
    )

    return render_template(
        "militaries/list.html",
        militaries=militaries,
        counts=military_service.count_militaries(),
        functional_types=FunctionalType,
        teams=team_service.list_teams(),
        filters={
            "status": valid_status or "",
            "functional_type": valid_functional_type or "",
            "q": query,
            "team": team_filter if valid_team_id or without_team else "",
        },
    )


@militaries_bp.get("/novo")
def create_military_form():
    return render_template(
        "militaries/create.html",
        form_data={"is_active": True},
        errors={},
        functional_types=FunctionalType,
    )


@militaries_bp.post("/novo")
def create_military():
    validation = validate_military_payload(request.form)
    if not validation.is_valid:
        return _render_create_form(validation.errors), 400

    try:
        military = military_service.create_military(validation.data)
    except MilitaryServiceError as error:
        return _render_create_form(error.errors), 400

    flash("Militar criado com sucesso.", "success")
    return redirect(url_for("militaries.detail_military", military_id=military.id))


@militaries_bp.get("/<int:military_id>")
def detail_military(military_id: int):
    military = military_service.get_military_or_404(military_id)
    return render_template(
        "militaries/detail.html",
        military=military,
        future_unavailabilities_count=unavailability_service.count_future_unavailabilities_for_military(military.id),
        next_unavailability=unavailability_service.next_unavailability_for_military(military.id),
    )


@militaries_bp.get("/<int:military_id>/editar")
def edit_military_form(military_id: int):
    military = military_service.get_military_or_404(military_id)
    return render_template(
        "militaries/edit.html",
        military=military,
        form_data=_form_data_from_military(military),
        errors={},
        functional_types=FunctionalType,
    )


@militaries_bp.post("/<int:military_id>/editar")
def edit_military(military_id: int):
    military = military_service.get_military_or_404(military_id)
    validation = validate_military_payload(request.form)
    if not validation.is_valid:
        return _render_edit_form(military, validation.errors), 400

    try:
        military_service.update_military(military, validation.data)
    except MilitaryServiceError as error:
        return _render_edit_form(military, error.errors), 400

    flash("Militar atualizado com sucesso.", "success")
    return redirect(url_for("militaries.detail_military", military_id=military.id))


@militaries_bp.post("/<int:military_id>/ativar")
def activate_military(military_id: int):
    military = military_service.get_military_or_404(military_id)
    military_service.activate_military(military)
    if military.has_inactive_date_warning():
        flash(
            "Militar ativado, mas a data de fim já passou. Reveja as datas antes de o usar em futuras funcionalidades.",
            "warning",
        )
    else:
        flash("Militar ativado com sucesso.", "success")
    return redirect(url_for("militaries.detail_military", military_id=military.id))


@militaries_bp.post("/<int:military_id>/desativar")
def deactivate_military(military_id: int):
    military = military_service.get_military_or_404(military_id)
    military_service.deactivate_military(military)
    flash("Militar desativado. O registo foi preservado.", "success")
    return redirect(url_for("militaries.detail_military", military_id=military.id))


def _render_create_form(errors: dict):
    return render_template(
        "militaries/create.html",
        form_data=_form_data_from_request(),
        errors=errors,
        functional_types=FunctionalType,
    )


def _render_edit_form(military, errors: dict):
    return render_template(
        "militaries/edit.html",
        military=military,
        form_data=_form_data_from_request(),
        errors=errors,
        functional_types=FunctionalType,
    )


def _form_data_from_request() -> dict:
    return {
        "name": request.form.get("name", ""),
        "nim": request.form.get("nim", ""),
        "functional_type": request.form.get("functional_type", ""),
        "is_active": "is_active" in request.form,
        "start_date": request.form.get("start_date", ""),
        "end_date": request.form.get("end_date", ""),
        "notes": request.form.get("notes", ""),
    }


def _form_data_from_military(military) -> dict:
    return {
        "name": military.name,
        "nim": military.nim,
        "functional_type": military.functional_type,
        "is_active": military.is_active,
        "start_date": military.start_date.isoformat(),
        "end_date": military.end_date.isoformat() if military.end_date else "",
        "notes": military.notes or "",
    }
