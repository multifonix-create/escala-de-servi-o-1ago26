from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.models import RestrictionType, WEEKDAY_FIELDS
from app.services import military_service, restriction_evaluator, restriction_service
from app.services.restriction_service import RestrictionServiceError
from app.validators import validate_restriction_payload, validate_restriction_test_payload


restrictions_bp = Blueprint("restrictions", __name__, url_prefix="/restricoes")
military_restrictions_bp = Blueprint(
    "military_restrictions",
    __name__,
    url_prefix="/militares",
)


@restrictions_bp.get("")
def list_restrictions():
    military_id = request.args.get("military_id", "").strip()
    restriction_type = request.args.get("restriction_type", "").strip()
    status = request.args.get("status", "").strip()
    valid_military_id = int(military_id) if military_id.isdigit() else None
    valid_type = restriction_type if restriction_type in {item.value for item in RestrictionType} else None
    valid_status = status if status in {"active", "inactive"} else None
    restrictions = restriction_service.list_restrictions(
        military_id=valid_military_id,
        restriction_type=valid_type,
        status=valid_status,
    )
    return render_template(
        "restrictions/list.html",
        restrictions=restrictions,
        militaries=military_service.list_militaries(),
        restriction_types=RestrictionType,
        filters={
            "military_id": str(valid_military_id or ""),
            "restriction_type": valid_type or "",
            "status": valid_status or "",
        },
        weekdays_summary=restriction_service.weekdays_summary,
    )


@military_restrictions_bp.get("/<int:military_id>/restricoes")
def military_restrictions(military_id: int):
    military = military_service.get_military_or_404(military_id)
    return render_template(
        "restrictions/military_list.html",
        military=military,
        restrictions=restriction_service.list_restrictions_for_military(military.id),
        weekdays_summary=restriction_service.weekdays_summary,
    )


@military_restrictions_bp.get("/<int:military_id>/restricoes/nova")
def new_restriction_form(military_id: int):
    military = military_service.get_military_or_404(military_id)
    return render_template(
        "restrictions/create.html",
        military=military,
        form_data={"is_active": True, "is_full_day": True},
        errors={},
        restriction_types=RestrictionType,
        weekday_fields=WEEKDAY_FIELDS,
    )


@military_restrictions_bp.post("/<int:military_id>/restricoes/nova")
def create_restriction(military_id: int):
    military = military_service.get_military_or_404(military_id)
    validation = validate_restriction_payload(request.form)
    if not validation.is_valid:
        return _render_create_form(military, validation.errors), 400
    try:
        restriction = restriction_service.create_restriction(military, validation.data)
    except RestrictionServiceError as error:
        return _render_create_form(military, error.errors), 400
    flash("Restrição criada com sucesso.", "success")
    return redirect(
        url_for(
            "military_restrictions.detail_restriction",
            military_id=military.id,
            restriction_id=restriction.id,
        )
    )


@military_restrictions_bp.get("/<int:military_id>/restricoes/<int:restriction_id>")
def detail_restriction(military_id: int, restriction_id: int):
    military = military_service.get_military_or_404(military_id)
    restriction = _get_restriction_for_military(military.id, restriction_id)
    return render_template(
        "restrictions/detail.html",
        military=military,
        restriction=restriction,
        weekdays_summary=restriction_service.weekdays_summary,
    )


@military_restrictions_bp.get("/<int:military_id>/restricoes/<int:restriction_id>/editar")
def edit_restriction_form(military_id: int, restriction_id: int):
    military = military_service.get_military_or_404(military_id)
    restriction = _get_restriction_for_military(military.id, restriction_id)
    return render_template(
        "restrictions/edit.html",
        military=military,
        restriction=restriction,
        form_data=_form_data_from_restriction(restriction),
        errors={},
        restriction_types=RestrictionType,
        weekday_fields=WEEKDAY_FIELDS,
    )


@military_restrictions_bp.post("/<int:military_id>/restricoes/<int:restriction_id>/editar")
def edit_restriction(military_id: int, restriction_id: int):
    military = military_service.get_military_or_404(military_id)
    restriction = _get_restriction_for_military(military.id, restriction_id)
    validation = validate_restriction_payload(request.form)
    if not validation.is_valid:
        return _render_edit_form(military, restriction, validation.errors), 400
    try:
        restriction_service.update_restriction(restriction, validation.data)
    except RestrictionServiceError as error:
        return _render_edit_form(military, restriction, error.errors), 400
    flash("Restrição atualizada com sucesso.", "success")
    return redirect(
        url_for(
            "military_restrictions.detail_restriction",
            military_id=military.id,
            restriction_id=restriction.id,
        )
    )


@military_restrictions_bp.post("/<int:military_id>/restricoes/<int:restriction_id>/ativar")
def activate_restriction(military_id: int, restriction_id: int):
    military = military_service.get_military_or_404(military_id)
    restriction = _get_restriction_for_military(military.id, restriction_id)
    restriction_service.activate_restriction(restriction)
    flash("Restrição ativada com sucesso.", "success")
    return redirect(url_for("military_restrictions.detail_restriction", military_id=military.id, restriction_id=restriction.id))


@military_restrictions_bp.post("/<int:military_id>/restricoes/<int:restriction_id>/desativar")
def deactivate_restriction(military_id: int, restriction_id: int):
    military = military_service.get_military_or_404(military_id)
    restriction = _get_restriction_for_military(military.id, restriction_id)
    restriction_service.deactivate_restriction(restriction)
    flash("Restrição desativada. O histórico foi preservado.", "success")
    return redirect(url_for("military_restrictions.detail_restriction", military_id=military.id, restriction_id=restriction.id))


@military_restrictions_bp.get("/<int:military_id>/restricoes/testar")
def test_restrictions_form(military_id: int):
    military = military_service.get_military_or_404(military_id)
    return render_template(
        "restrictions/test.html",
        military=military,
        form_data={},
        errors={},
        evaluation=None,
    )


@military_restrictions_bp.post("/<int:military_id>/restricoes/testar")
def test_restrictions(military_id: int):
    military = military_service.get_military_or_404(military_id)
    validation = validate_restriction_test_payload(request.form)
    evaluation = None
    if validation.is_valid:
        evaluation = restriction_evaluator.evaluate_service_interval(
            military.id,
            validation.data["service_start"],
            validation.data["service_end"],
        )
    return render_template(
        "restrictions/test.html",
        military=military,
        form_data=_test_form_data_from_request(),
        errors=validation.errors,
        evaluation=evaluation,
    ), 200 if validation.is_valid else 400


def _render_create_form(military, errors: dict):
    return render_template(
        "restrictions/create.html",
        military=military,
        form_data=_form_data_from_request(),
        errors=errors,
        restriction_types=RestrictionType,
        weekday_fields=WEEKDAY_FIELDS,
    )


def _render_edit_form(military, restriction, errors: dict):
    return render_template(
        "restrictions/edit.html",
        military=military,
        restriction=restriction,
        form_data=_form_data_from_request(),
        errors=errors,
        restriction_types=RestrictionType,
        weekday_fields=WEEKDAY_FIELDS,
    )


def _get_restriction_for_military(military_id: int, restriction_id: int):
    restriction = restriction_service.get_restriction_or_404(restriction_id)
    if restriction.military_id != military_id:
        abort(404)
    return restriction


def _form_data_from_request() -> dict:
    data = {
        "restriction_type": request.form.get("restriction_type", ""),
        "start_date": request.form.get("start_date", ""),
        "end_date": request.form.get("end_date", ""),
        "start_time": request.form.get("start_time", ""),
        "end_time": request.form.get("end_time", ""),
        "is_full_day": "is_full_day" in request.form,
        "is_active": "is_active" in request.form,
        "reason": request.form.get("reason", ""),
        "notes": request.form.get("notes", ""),
    }
    data.update({field: field in request.form for field in WEEKDAY_FIELDS})
    return data


def _form_data_from_restriction(restriction) -> dict:
    data = {
        "restriction_type": restriction.restriction_type,
        "start_date": restriction.start_date.isoformat(),
        "end_date": restriction.end_date.isoformat() if restriction.end_date else "",
        "start_time": restriction.start_time.strftime("%H:%M") if restriction.start_time else "",
        "end_time": restriction.end_time.strftime("%H:%M") if restriction.end_time else "",
        "is_full_day": restriction.is_full_day,
        "is_active": restriction.is_active,
        "reason": restriction.reason,
        "notes": restriction.notes or "",
    }
    data.update({field: getattr(restriction, field) for field in WEEKDAY_FIELDS})
    return data


def _test_form_data_from_request() -> dict:
    return {
        "service_date": request.form.get("service_date", ""),
        "start_time": request.form.get("start_time", ""),
        "end_time": request.form.get("end_time", ""),
        "description": request.form.get("description", ""),
    }
