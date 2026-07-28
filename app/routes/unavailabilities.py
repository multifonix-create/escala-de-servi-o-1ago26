from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.models import CompensationStatus, UnavailabilityCode, UnavailabilityStatus
from app.services import availability_evaluator, military_service, unavailability_service
from app.services.unavailability_service import UnavailabilityServiceError
from app.validators import validate_availability_test_payload, validate_unavailability_payload


unavailabilities_bp = Blueprint("unavailabilities", __name__, url_prefix="/indisponibilidades")
military_unavailabilities_bp = Blueprint("military_unavailabilities", __name__, url_prefix="/militares")


@unavailabilities_bp.get("")
def list_unavailabilities():
    filters = _filters_from_request()
    unavailabilities = unavailability_service.list_unavailabilities(**filters["values"])
    return render_template(
        "unavailabilities/list.html",
        unavailabilities=unavailabilities,
        militaries=military_service.list_militaries(),
        codes=UnavailabilityCode,
        statuses=UnavailabilityStatus,
        filters=filters["display"],
        format_code=unavailability_service.format_code,
        cycle_coincidences_for=_cycle_coincidences_for,
    )


@military_unavailabilities_bp.get("/<int:military_id>/indisponibilidades")
def military_unavailabilities(military_id: int):
    military = military_service.get_military_or_404(military_id)
    return render_template(
        "unavailabilities/military_list.html",
        military=military,
        unavailabilities=unavailability_service.list_unavailabilities_for_military(military.id),
        format_code=unavailability_service.format_code,
        cycle_coincidences_for=_cycle_coincidences_for,
    )


@military_unavailabilities_bp.get("/<int:military_id>/indisponibilidades/nova")
def new_unavailability_form(military_id: int):
    military = military_service.get_military_or_404(military_id)
    return _render_create_form(military, {}, {"is_full_day": True, "status": "PLANNED", "compensation_status": "NOT_APPLICABLE"})


@military_unavailabilities_bp.post("/<int:military_id>/indisponibilidades/nova")
def create_unavailability(military_id: int):
    military = military_service.get_military_or_404(military_id)
    validation = validate_unavailability_payload(request.form)
    if not validation.is_valid:
        return _render_create_form(military, validation.errors, _form_data_from_request()), 400
    try:
        unavailability, overlaps = unavailability_service.create_unavailability(military, validation.data)
    except UnavailabilityServiceError as error:
        return _render_create_form(military, error.errors, _form_data_from_request()), 400
    if overlaps:
        flash("Indisponibilidade criada com aviso: existe sobreposição com outro registo.", "warning")
    else:
        flash("Indisponibilidade criada com sucesso.", "success")
    return redirect(url_for("military_unavailabilities.detail_unavailability", military_id=military.id, unavailability_id=unavailability.id))


@military_unavailabilities_bp.get("/<int:military_id>/indisponibilidades/testar")
def test_availability_form(military_id: int):
    military = military_service.get_military_or_404(military_id)
    return render_template("unavailabilities/test.html", military=military, form_data={}, errors={}, evaluation=None)


@military_unavailabilities_bp.post("/<int:military_id>/indisponibilidades/testar")
def test_availability(military_id: int):
    military = military_service.get_military_or_404(military_id)
    validation = validate_availability_test_payload(request.form)
    evaluation = None
    if validation.is_valid:
        evaluation = availability_evaluator.evaluate_service_interval(
            military.id,
            validation.data["service_start"],
            validation.data["service_end"],
        )
    return render_template(
        "unavailabilities/test.html",
        military=military,
        form_data=_test_form_data_from_request(),
        errors=validation.errors,
        evaluation=evaluation,
    ), 200 if validation.is_valid else 400


@military_unavailabilities_bp.get("/<int:military_id>/indisponibilidades/<int:unavailability_id>")
def detail_unavailability(military_id: int, unavailability_id: int):
    military = military_service.get_military_or_404(military_id)
    unavailability = _get_unavailability_for_military(military.id, unavailability_id)
    return render_template(
        "unavailabilities/detail.html",
        military=military,
        unavailability=unavailability,
        format_code=unavailability_service.format_code,
        cycle_coincidences=unavailability_service.calculate_cycle_coincidences(military, unavailability.start_date, unavailability.end_date),
    )


@military_unavailabilities_bp.get("/<int:military_id>/indisponibilidades/<int:unavailability_id>/editar")
def edit_unavailability_form(military_id: int, unavailability_id: int):
    military = military_service.get_military_or_404(military_id)
    unavailability = _get_unavailability_for_military(military.id, unavailability_id)
    return _render_edit_form(military, unavailability, {}, _form_data_from_unavailability(unavailability))


@military_unavailabilities_bp.post("/<int:military_id>/indisponibilidades/<int:unavailability_id>/editar")
def edit_unavailability(military_id: int, unavailability_id: int):
    military = military_service.get_military_or_404(military_id)
    unavailability = _get_unavailability_for_military(military.id, unavailability_id)
    validation = validate_unavailability_payload(request.form)
    if not validation.is_valid:
        return _render_edit_form(military, unavailability, validation.errors, _form_data_from_request()), 400
    try:
        _, overlaps = unavailability_service.update_unavailability(unavailability, validation.data)
    except UnavailabilityServiceError as error:
        return _render_edit_form(military, unavailability, error.errors, _form_data_from_request()), 400
    flash("Indisponibilidade atualizada com sucesso." if not overlaps else "Indisponibilidade atualizada com aviso de sobreposição.", "success" if not overlaps else "warning")
    return redirect(url_for("military_unavailabilities.detail_unavailability", military_id=military.id, unavailability_id=unavailability.id))


@military_unavailabilities_bp.post("/<int:military_id>/indisponibilidades/<int:unavailability_id>/confirmar")
def confirm_unavailability(military_id: int, unavailability_id: int):
    military = military_service.get_military_or_404(military_id)
    unavailability = _get_unavailability_for_military(military.id, unavailability_id)
    try:
        unavailability_service.confirm_unavailability(unavailability)
    except UnavailabilityServiceError as error:
        flash(next(iter(error.errors.values())), "warning")
    else:
        flash("Indisponibilidade confirmada.", "success")
    return redirect(url_for("military_unavailabilities.detail_unavailability", military_id=military.id, unavailability_id=unavailability.id))


@military_unavailabilities_bp.post("/<int:military_id>/indisponibilidades/<int:unavailability_id>/cancelar")
def cancel_unavailability(military_id: int, unavailability_id: int):
    military = military_service.get_military_or_404(military_id)
    unavailability = _get_unavailability_for_military(military.id, unavailability_id)
    unavailability_service.cancel_unavailability(unavailability)
    flash("Indisponibilidade cancelada. O histórico foi preservado.", "success")
    return redirect(url_for("military_unavailabilities.detail_unavailability", military_id=military.id, unavailability_id=unavailability.id))


@military_unavailabilities_bp.post("/<int:military_id>/indisponibilidades/<int:unavailability_id>/reativar")
def reactivate_unavailability(military_id: int, unavailability_id: int):
    military = military_service.get_military_or_404(military_id)
    unavailability = _get_unavailability_for_military(military.id, unavailability_id)
    try:
        unavailability_service.reactivate_unavailability(unavailability)
    except UnavailabilityServiceError as error:
        flash(next(iter(error.errors.values())), "warning")
    else:
        flash("Indisponibilidade reativada como planeada.", "success")
    return redirect(url_for("military_unavailabilities.detail_unavailability", military_id=military.id, unavailability_id=unavailability.id))


def _render_create_form(military, errors: dict, form_data: dict):
    return render_template("unavailabilities/create.html", military=military, form_data=form_data, errors=errors, codes=UnavailabilityCode, statuses=UnavailabilityStatus, compensation_statuses=CompensationStatus)


def _render_edit_form(military, unavailability, errors: dict, form_data: dict):
    return render_template("unavailabilities/edit.html", military=military, unavailability=unavailability, form_data=form_data, errors=errors, codes=UnavailabilityCode, statuses=UnavailabilityStatus, compensation_statuses=CompensationStatus)


def _get_unavailability_for_military(military_id: int, unavailability_id: int):
    unavailability = unavailability_service.get_unavailability_or_404(unavailability_id)
    if unavailability.military_id != military_id:
        abort(404)
    return unavailability


def _filters_from_request() -> dict:
    military_id = request.args.get("military_id", "").strip()
    code = request.args.get("code", "").strip()
    status = request.args.get("status", "").strip()
    start = request.args.get("start_date", "").strip()
    end = request.args.get("end_date", "").strip()
    return {
        "values": {
            "military_id": int(military_id) if military_id.isdigit() else None,
            "code": code if code in {item.value for item in UnavailabilityCode} else None,
            "status": status if status in {item.value for item in UnavailabilityStatus} else None,
            "start_date": date.fromisoformat(start) if start else None,
            "end_date": date.fromisoformat(end) if end else None,
        },
        "display": {"military_id": military_id, "code": code, "status": status, "start_date": start, "end_date": end},
    }


def _form_data_from_request() -> dict:
    return {key: request.form.get(key, "") for key in ("code", "status", "start_date", "end_date", "start_time", "end_time", "reason", "location", "travel_minutes_before", "travel_minutes_after", "compensation_status", "compensation_notes")} | {"is_full_day": "is_full_day" in request.form}


def _form_data_from_unavailability(item) -> dict:
    return {
        "code": item.code,
        "status": item.status,
        "start_date": item.start_date.isoformat(),
        "end_date": item.end_date.isoformat(),
        "start_time": item.start_time.strftime("%H:%M") if item.start_time else "",
        "end_time": item.end_time.strftime("%H:%M") if item.end_time else "",
        "is_full_day": item.is_full_day,
        "reason": item.reason,
        "location": item.location or "",
        "travel_minutes_before": str(item.travel_minutes_before),
        "travel_minutes_after": str(item.travel_minutes_after),
        "compensation_status": item.compensation_status,
        "compensation_notes": item.compensation_notes or "",
    }


def _test_form_data_from_request() -> dict:
    return {key: request.form.get(key, "") for key in ("start_date", "start_time", "end_date", "end_time", "description")}


def _cycle_coincidences_for(unavailability):
    return unavailability_service.calculate_cycle_coincidences(unavailability.military, unavailability.start_date, unavailability.end_date)
