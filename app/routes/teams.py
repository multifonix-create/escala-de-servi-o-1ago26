from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.services import membership_service, military_service, team_service
from app.services.membership_service import MembershipServiceError
from app.validators import validate_membership_payload


teams_bp = Blueprint("teams", __name__, url_prefix="/equipas")
military_teams_bp = Blueprint("military_teams", __name__, url_prefix="/militares")


@teams_bp.get("")
def list_teams():
    teams = team_service.list_teams()
    member_counts = {
        team.id: team_service.count_current_members(team.id)
        for team in teams
    }
    return render_template(
        "teams/list.html",
        teams=teams,
        member_counts=member_counts,
    )


@teams_bp.get("/<int:team_id>")
def detail_team(team_id: int):
    team = team_service.get_team_or_404(team_id)
    return render_template(
        "teams/detail.html",
        team=team,
        current_members=membership_service.list_current_members_for_team(team.id),
        history=membership_service.list_history_for_team(team.id),
    )


@military_teams_bp.get("/<int:military_id>/equipa")
def show_military_team(military_id: int):
    military = military_service.get_military_or_404(military_id)
    return render_template(
        "memberships/associate.html",
        military=military,
        teams=team_service.list_teams(),
        form_data={"start_date": military.start_date.isoformat()},
        errors={},
    )


@military_teams_bp.post("/<int:military_id>/equipa/associar")
def associate_military_team(military_id: int):
    military = military_service.get_military_or_404(military_id)
    validation = validate_membership_payload(request.form)
    if not validation.is_valid:
        return _render_associate_form(military, validation.errors), 400

    team = team_service.get_team(validation.data["team_id"])
    try:
        membership_service.assign_military_to_team(
            military,
            team,
            validation.data["start_date"],
            validation.data["reason"],
        )
    except MembershipServiceError as error:
        return _render_associate_form(military, error.errors), 400

    flash("Equipa associada com sucesso.", "success")
    return redirect(url_for("militaries.detail_military", military_id=military.id))


@military_teams_bp.get("/<int:military_id>/equipa/mudar")
def change_military_team_form(military_id: int):
    military = military_service.get_military_or_404(military_id)
    return render_template(
        "memberships/change.html",
        military=military,
        teams=team_service.list_teams(),
        form_data={},
        errors={},
    )


@military_teams_bp.post("/<int:military_id>/equipa/mudar")
def change_military_team(military_id: int):
    military = military_service.get_military_or_404(military_id)
    validation = validate_membership_payload(request.form)
    if not validation.is_valid:
        return _render_change_form(military, validation.errors), 400

    team = team_service.get_team(validation.data["team_id"])
    try:
        membership_service.change_military_team(
            military,
            team,
            validation.data["start_date"],
            validation.data["reason"],
        )
    except MembershipServiceError as error:
        return _render_change_form(military, error.errors), 400

    flash("Equipa alterada com sucesso. O historico foi preservado.", "success")
    return redirect(url_for("militaries.detail_military", military_id=military.id))


@military_teams_bp.get("/<int:military_id>/historico-equipas")
def military_team_history(military_id: int):
    military = military_service.get_military_or_404(military_id)
    return render_template(
        "memberships/history.html",
        military=military,
        memberships=membership_service.list_memberships_for_military(military.id),
    )


@military_teams_bp.get("/<int:military_id>/historico-equipas/<int:membership_id>/editar")
def edit_membership_form(military_id: int, membership_id: int):
    military = military_service.get_military_or_404(military_id)
    membership = _get_membership_for_military(military.id, membership_id)
    return render_template(
        "memberships/edit.html",
        military=military,
        membership=membership,
        form_data=_form_data_from_membership(membership),
        errors={},
    )


@military_teams_bp.post("/<int:military_id>/historico-equipas/<int:membership_id>/editar")
def edit_membership(military_id: int, membership_id: int):
    military = military_service.get_military_or_404(military_id)
    membership = _get_membership_for_military(military.id, membership_id)
    validation = validate_membership_payload(
        request.form,
        require_team=False,
        allow_end_date=True,
    )
    if not validation.is_valid:
        return _render_edit_form(military, membership, validation.errors), 400

    try:
        membership_service.update_membership(
            membership,
            validation.data["start_date"],
            validation.data["end_date"],
            validation.data["reason"],
        )
    except MembershipServiceError as error:
        return _render_edit_form(military, membership, error.errors), 400

    flash("Historico de equipa atualizado com sucesso.", "success")
    return redirect(url_for("military_teams.military_team_history", military_id=military.id))


def _render_associate_form(military, errors: dict):
    return render_template(
        "memberships/associate.html",
        military=military,
        teams=team_service.list_teams(),
        form_data=_form_data_from_request(),
        errors=errors,
    )


def _render_change_form(military, errors: dict):
    return render_template(
        "memberships/change.html",
        military=military,
        teams=team_service.list_teams(),
        form_data=_form_data_from_request(),
        errors=errors,
    )


def _render_edit_form(military, membership, errors: dict):
    return render_template(
        "memberships/edit.html",
        military=military,
        membership=membership,
        form_data=_form_data_from_request(),
        errors=errors,
    )


def _get_membership_for_military(military_id: int, membership_id: int):
    membership = membership_service.get_membership_or_404(membership_id)
    if membership.military_id != military_id:
        abort(404)
    return membership


def _form_data_from_request() -> dict:
    return {
        "team_id": request.form.get("team_id", ""),
        "start_date": request.form.get("start_date", ""),
        "end_date": request.form.get("end_date", ""),
        "reason": request.form.get("reason", ""),
    }


def _form_data_from_membership(membership) -> dict:
    return {
        "team_id": membership.team_id,
        "start_date": membership.start_date.isoformat(),
        "end_date": membership.end_date.isoformat() if membership.end_date else "",
        "reason": membership.reason or "",
    }
