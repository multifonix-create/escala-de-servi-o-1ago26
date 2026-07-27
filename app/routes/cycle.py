from datetime import date, timedelta

from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.services import cycle_calculator, team_service
from app.services.cycle_calculator import CycleCalculationError, MissingTeamReferenceError
from app.validators import validate_cycle_reference_payload, validate_preview_payload


cycle_bp = Blueprint("cycle", __name__, url_prefix="/ciclo")
team_cycle_bp = Blueprint("team_cycle", __name__, url_prefix="/equipas")


@cycle_bp.get("")
def overview():
    selected_date = _parse_query_date(request.args.get("date", ""))
    week_start = cycle_calculator.monday_of_week(selected_date)
    week_end = week_start + timedelta(days=6)
    rows = []
    for team in team_service.list_teams():
        try:
            selected_day = cycle_calculator.calculate_team_day(team, selected_date)
            week_days = cycle_calculator.preview_team_cycle(team, week_start, week_end)
            rows.append(
                {
                    "team": team,
                    "configured": True,
                    "reference": cycle_calculator.get_reference_for_team_on_date(
                        team.id,
                        selected_date,
                    ),
                    "selected_day": selected_day,
                    "week_days": week_days,
                }
            )
        except MissingTeamReferenceError:
            rows.append(
                {
                    "team": team,
                    "configured": False,
                    "reference": None,
                    "selected_day": None,
                    "week_days": [],
                }
            )

    return render_template(
        "cycle/overview.html",
        selected_date=selected_date,
        week_start=week_start,
        week_end=week_end,
        rows=rows,
    )


@cycle_bp.get("/configurar")
def configure():
    return render_template("cycle/configure.html", teams=team_service.list_teams())


@cycle_bp.get("/pre-visualizar")
def preview():
    validation = validate_preview_payload(request.args)
    teams = team_service.list_teams()
    selected_team = team_service.get_team(validation.data["team_id"]) if validation.data["team_id"] else None
    preview_days = []
    errors = dict(validation.errors)

    if validation.is_valid:
        try:
            cycle_calculator.validate_team(selected_team)
            preview_days = cycle_calculator.preview_team_cycle(
                selected_team,
                validation.data["start_date"],
                validation.data["end_date"],
            )
        except CycleCalculationError as error:
            errors.update(error.errors)

    return render_template(
        "cycle/preview.html",
        teams=teams,
        selected_team=selected_team,
        preview_days=preview_days,
        form_data={
            "team_id": request.args.get("team_id", ""),
            "start_date": request.args.get("start_date", validation.data["start_date"].isoformat() if validation.data["start_date"] else ""),
            "end_date": request.args.get("end_date", validation.data["end_date"].isoformat() if validation.data["end_date"] else ""),
        },
        errors=errors,
    )


@team_cycle_bp.get("/<int:team_id>/ciclo")
def team_cycle(team_id: int):
    team = team_service.get_team_or_404(team_id)
    today = date.today()
    reference = cycle_calculator.get_reference_for_team_on_date(team.id, today)
    try:
        preview_days = cycle_calculator.preview_team_cycle(team, today, today + timedelta(days=13))
    except MissingTeamReferenceError:
        preview_days = []
    return render_template(
        "cycle/team_cycle.html",
        team=team,
        reference=reference,
        preview_days=preview_days,
    )


@team_cycle_bp.get("/<int:team_id>/ciclo/nova-referencia")
def new_reference_form(team_id: int):
    team = team_service.get_team_or_404(team_id)
    today = date.today()
    return render_template(
        "cycle/new_reference.html",
        team=team,
        form_data={
            "reference_date": today.isoformat(),
            "valid_from": today.isoformat(),
            "reference_phase": "",
            "notes": "",
        },
        errors={},
        preview_days=[],
    )


@team_cycle_bp.post("/<int:team_id>/ciclo/nova-referencia")
def create_reference(team_id: int):
    team = team_service.get_team_or_404(team_id)
    validation = validate_cycle_reference_payload(request.form)
    preview_days = []
    if validation.is_valid:
        preview_days = _preview_reference_before_save(team, validation.data)
        try:
            cycle_calculator.create_team_cycle_reference(team, **validation.data)
        except CycleCalculationError as error:
            return _render_reference_form(team, error.errors, preview_days), 400
        flash("Referência do ciclo criada com sucesso. O histórico foi preservado.", "success")
        return redirect(url_for("team_cycle.team_cycle", team_id=team.id))

    return _render_reference_form(team, validation.errors, preview_days), 400


@team_cycle_bp.get("/<int:team_id>/ciclo/historico")
def reference_history(team_id: int):
    team = team_service.get_team_or_404(team_id)
    return render_template(
        "cycle/history.html",
        team=team,
        references=cycle_calculator.list_references_for_team(team.id),
    )


def _render_reference_form(team, errors: dict, preview_days: list):
    return render_template(
        "cycle/new_reference.html",
        team=team,
        form_data=_form_data_from_request(),
        errors=errors,
        preview_days=preview_days,
    )


def _preview_reference_before_save(team, data: dict) -> list:
    temporary_reference = type(
        "TemporaryReference",
        (),
        {
            "id": 0,
            "team": team,
            "team_id": team.id,
            "reference_date": data["reference_date"],
            "reference_phase": data["reference_phase"],
            "valid_from": data["valid_from"],
            "valid_until": None,
        },
    )()
    days = []
    current = data["valid_from"]
    end_date = current + timedelta(days=13)
    while current <= end_date:
        phase = cycle_calculator.calculate_phase(
            temporary_reference.reference_phase,
            temporary_reference.reference_date,
            current,
        )
        code = cycle_calculator.day_off_code_for_phase(phase, current)
        days.append(
            {
                "day": current,
                "weekday_name": cycle_calculator.WEEKDAY_NAMES[current.weekday()],
                "phase": phase,
                "code": code,
            }
        )
        current += timedelta(days=1)
    return days


def _form_data_from_request() -> dict:
    return {
        "reference_date": request.form.get("reference_date", ""),
        "reference_phase": request.form.get("reference_phase", ""),
        "valid_from": request.form.get("valid_from", ""),
        "notes": request.form.get("notes", ""),
    }


def _parse_query_date(value: str) -> date:
    try:
        return date.fromisoformat(value) if value else date.today()
    except ValueError:
        return date.today()
