from datetime import date

import click
from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from app.extensions import db
from app.models import (
    COMPENSATORY_LEAVE_CREDIT_STATUS_LABELS,
    COMPENSATORY_LEAVE_SOURCE_TYPE_LABELS,
    RESCHEDULED_REST_CREDIT_STATUS_LABELS,
    CompensatoryLeaveCredit,
    Military,
    RescheduledRestCredit,
    ScheduleVersion,
)
from app.services.compensation_service import (
    CompensationMaintenanceService,
    CompensationServiceError,
    cancel_fc_right,
    cancel_fc_schedule,
    cancel_fr_right,
    cancel_fr_schedule,
    confirm_fc_from_assignment,
    confirm_fr_from_assignment,
    confirm_fr_used,
    create_commander_discretionary_credit,
    fc_balance_by_military,
    fr_balance_by_military,
    list_compensation_potentials,
    list_fc_credits,
    list_fr_credits,
    reschedule_fc_credit,
    reschedule_fr_credit,
    schedule_fc_credit,
    schedule_fr_credit,
)
from app.services.schedule_service import get_schedule_month, get_version_for_month_or_404, list_versions


compensations_bp = Blueprint("compensations", __name__)


@compensations_bp.get("/fc")
def fc_index():
    status = request.args.get("status") or None
    return render_template(
        "compensations/fc_list.html",
        credits=list_fc_credits(status=status),
        balances=fc_balance_by_military(),
        status_labels=COMPENSATORY_LEAVE_CREDIT_STATUS_LABELS,
        source_labels=COMPENSATORY_LEAVE_SOURCE_TYPE_LABELS,
        selected_status=status or "",
    )


@compensations_bp.route("/fc/novo", methods=["GET", "POST"])
def create_fc_route():
    militaries = Military.query.order_by(Military.name.asc(), Military.nim.asc()).all()
    errors = {}
    if request.method == "POST":
        try:
            credits = create_commander_discretionary_credit(request.form)
        except CompensationServiceError as exc:
            errors = exc.errors
            _flash_error(exc)
            return render_template("compensations/fc_form.html", militaries=militaries, errors=errors), 400
        flash(f"FC criadas por decisao de comando: {len(credits)}.", "success")
        return redirect(url_for("compensations.fc_index"))
    return render_template("compensations/fc_form.html", militaries=militaries, errors=errors)


@compensations_bp.get("/fc/<int:credit_id>")
def fc_detail(credit_id: int):
    CompensationMaintenanceService().process()
    credit = db.get_or_404(CompensatoryLeaveCredit, credit_id)
    return render_template(
        "compensations/fc_detail.html",
        credit=credit,
        status_labels=COMPENSATORY_LEAVE_CREDIT_STATUS_LABELS,
        source_labels=COMPENSATORY_LEAVE_SOURCE_TYPE_LABELS,
    )


@compensations_bp.route("/fc/<int:credit_id>/agendar", methods=["GET", "POST"])
def schedule_fc_route(credit_id: int):
    credit = db.get_or_404(CompensatoryLeaveCredit, credit_id)
    if request.method == "POST":
        try:
            schedule_fc_credit(credit, _schedule_version_from_form(), date.fromisoformat(request.form.get("scheduled_date", "")), request.form.get("notes"))
        except (CompensationServiceError, ValueError) as exc:
            _flash_error(exc)
            return _schedule_template(credit, "compensations/fc_schedule.html", 400)
        flash("FC agendada.", "success")
        return redirect(url_for("compensations.fc_detail", credit_id=credit.id))
    return _schedule_template(credit, "compensations/fc_schedule.html")


@compensations_bp.route("/fc/<int:credit_id>/reagendar", methods=["GET", "POST"])
def reschedule_fc_route(credit_id: int):
    credit = db.get_or_404(CompensatoryLeaveCredit, credit_id)
    if request.method == "POST":
        try:
            reschedule_fc_credit(credit, _schedule_version_from_form(), date.fromisoformat(request.form.get("scheduled_date", "")), request.form.get("notes"))
        except (CompensationServiceError, ValueError) as exc:
            _flash_error(exc)
            return _schedule_template(credit, "compensations/fc_schedule.html", 400)
        flash("FC reagendada.", "success")
        return redirect(url_for("compensations.fc_detail", credit_id=credit.id))
    return _schedule_template(credit, "compensations/fc_schedule.html")


@compensations_bp.post("/fc/<int:credit_id>/cancelar-agendamento")
def cancel_fc_schedule_route(credit_id: int):
    credit = db.get_or_404(CompensatoryLeaveCredit, credit_id)
    try:
        cancel_fc_schedule(credit, request.form.get("reason"))
    except CompensationServiceError as exc:
        _flash_error(exc)
    else:
        flash("Agendamento de FC cancelado.", "success")
    return redirect(url_for("compensations.fc_detail", credit_id=credit.id))


@compensations_bp.post("/fc/<int:credit_id>/cancelar-direito")
def cancel_fc_right_route(credit_id: int):
    credit = db.get_or_404(CompensatoryLeaveCredit, credit_id)
    try:
        cancel_fc_right(credit, request.form.get("reason"))
    except CompensationServiceError as exc:
        _flash_error(exc)
    else:
        flash("Direito FC cancelado.", "success")
    return redirect(url_for("compensations.fc_detail", credit_id=credit.id))


@compensations_bp.get("/fc/<int:credit_id>/historico")
def fc_history(credit_id: int):
    return render_template("compensations/fc_history.html", credit=db.get_or_404(CompensatoryLeaveCredit, credit_id))


@compensations_bp.get("/folgas-reagendadas")
def fr_index():
    status = request.args.get("status") or None
    return render_template(
        "compensations/fr_list.html",
        credits=list_fr_credits(status=status),
        balances=fr_balance_by_military(),
        status_labels=RESCHEDULED_REST_CREDIT_STATUS_LABELS,
        selected_status=status or "",
    )


@compensations_bp.get("/folgas-reagendadas/<int:credit_id>")
def fr_detail(credit_id: int):
    credit = db.get_or_404(RescheduledRestCredit, credit_id)
    return render_template("compensations/fr_detail.html", credit=credit, status_labels=RESCHEDULED_REST_CREDIT_STATUS_LABELS)


@compensations_bp.route("/folgas-reagendadas/<int:credit_id>/agendar", methods=["GET", "POST"])
def schedule_fr_route(credit_id: int):
    credit = db.get_or_404(RescheduledRestCredit, credit_id)
    if request.method == "POST":
        try:
            schedule_fr_credit(credit, _schedule_version_from_form(), date.fromisoformat(request.form.get("scheduled_date", "")), request.form.get("notes"))
        except (CompensationServiceError, ValueError) as exc:
            _flash_error(exc)
            return _schedule_template(credit, "compensations/fr_schedule.html", 400)
        flash("FR agendada.", "success")
        return redirect(url_for("compensations.fr_detail", credit_id=credit.id))
    return _schedule_template(credit, "compensations/fr_schedule.html")


@compensations_bp.route("/folgas-reagendadas/<int:credit_id>/reagendar", methods=["GET", "POST"])
def reschedule_fr_route(credit_id: int):
    credit = db.get_or_404(RescheduledRestCredit, credit_id)
    if request.method == "POST":
        try:
            reschedule_fr_credit(credit, _schedule_version_from_form(), date.fromisoformat(request.form.get("scheduled_date", "")), request.form.get("notes"))
        except (CompensationServiceError, ValueError) as exc:
            _flash_error(exc)
            return _schedule_template(credit, "compensations/fr_schedule.html", 400)
        flash("FR reagendada.", "success")
        return redirect(url_for("compensations.fr_detail", credit_id=credit.id))
    return _schedule_template(credit, "compensations/fr_schedule.html")


@compensations_bp.post("/folgas-reagendadas/<int:credit_id>/cancelar-agendamento")
def cancel_fr_schedule_route(credit_id: int):
    credit = db.get_or_404(RescheduledRestCredit, credit_id)
    try:
        cancel_fr_schedule(credit, request.form.get("reason"))
    except CompensationServiceError as exc:
        _flash_error(exc)
    else:
        flash("Agendamento de FR cancelado.", "success")
    return redirect(url_for("compensations.fr_detail", credit_id=credit.id))


@compensations_bp.post("/folgas-reagendadas/<int:credit_id>/confirmar-gozo")
def confirm_fr_used_route(credit_id: int):
    credit = db.get_or_404(RescheduledRestCredit, credit_id)
    try:
        confirm_fr_used(credit, request.form.get("description"))
    except CompensationServiceError as exc:
        _flash_error(exc)
    else:
        flash("Gozo de FR confirmado.", "success")
    return redirect(url_for("compensations.fr_detail", credit_id=credit.id))


@compensations_bp.post("/folgas-reagendadas/<int:credit_id>/cancelar-direito")
def cancel_fr_right_route(credit_id: int):
    credit = db.get_or_404(RescheduledRestCredit, credit_id)
    try:
        cancel_fr_right(credit, request.form.get("reason"))
    except CompensationServiceError as exc:
        _flash_error(exc)
    else:
        flash("Direito FR cancelado.", "success")
    return redirect(url_for("compensations.fr_detail", credit_id=credit.id))


@compensations_bp.get("/folgas-reagendadas/<int:credit_id>/historico")
def fr_history(credit_id: int):
    return render_template("compensations/fr_history.html", credit=db.get_or_404(RescheduledRestCredit, credit_id))


@compensations_bp.get("/escala/<int:year>/<int:month>/versoes/<int:version_id>/compensacoes/processar")
def process_compensations(year: int, month: int, version_id: int):
    schedule_month, version = _version_context(year, month, version_id)
    fc_potentials, fr_potentials = list_compensation_potentials(version)
    return render_template(
        "compensations/process.html",
        schedule_month=schedule_month,
        version=version,
        fc_potentials=fc_potentials,
        fr_potentials=fr_potentials,
        source_labels=COMPENSATORY_LEAVE_SOURCE_TYPE_LABELS,
    )


@compensations_bp.post("/escala/<int:year>/<int:month>/versoes/<int:version_id>/compensacoes/processar")
def create_compensations(year: int, month: int, version_id: int):
    _, version = _version_context(year, month, version_id)
    fc_ids = {int(value) for value in request.form.getlist("fc_assignment_id") if value.isdigit()}
    fr_ids = {int(value) for value in request.form.getlist("fr_assignment_id") if value.isdigit()}
    created_fc = 0
    created_fr = 0
    fc_potentials, fr_potentials = list_compensation_potentials(version)
    for candidate in fc_potentials:
        if candidate.assignment.id not in fc_ids or not candidate.is_new:
            continue
        try:
            created_fc += len(confirm_fc_from_assignment(candidate.assignment))
        except CompensationServiceError as exc:
            _flash_error(exc)
    for candidate in fr_potentials:
        if candidate.assignment.id not in fr_ids or not candidate.is_new:
            continue
        try:
            confirm_fr_from_assignment(candidate.assignment)
        except CompensationServiceError as exc:
            _flash_error(exc)
        else:
            created_fr += 1
    flash(f"Creditos criados: FC {created_fc}; FR {created_fr}.", "success")
    return redirect(url_for("compensations.process_compensations", year=year, month=month, version_id=version.id))


def register_cli(app):
    @app.cli.command("process-compensations")
    @click.option("--date", "process_date", default=None)
    def process_compensations_command(process_date: str | None):
        current = date.fromisoformat(process_date) if process_date else None
        summary = CompensationMaintenanceService().process(today=current)
        click.echo(f"FC expiradas: {summary['expired']}")
        click.echo(f"FC marcadas como gozadas automaticamente: {summary['auto_used']}")


def _schedule_template(credit, template: str, status_code: int = 200):
    source_version = getattr(credit, "source_schedule_version", None)
    if source_version is not None:
        versions = [
            version
            for version in list_versions(source_version.schedule_month.id)
            if version.status == "DRAFT"
        ]
    else:
        versions = ScheduleVersion.query.filter_by(status="DRAFT").order_by(ScheduleVersion.id.desc()).all()
    response = render_template(template, credit=credit, versions=versions)
    return (response, status_code) if status_code != 200 else response


def _schedule_version_from_form() -> ScheduleVersion:
    version_id = request.form.get("schedule_version_id")
    if not version_id or not version_id.isdigit():
        raise CompensationServiceError("Versao invalida.", {"schedule_version": "Escolha uma versao DRAFT."})
    version = db.session.get(ScheduleVersion, int(version_id))
    if version is None:
        raise CompensationServiceError("Versao inexistente.", {"schedule_version": "Escolha uma versao DRAFT."})
    return version


def _version_context(year: int, month: int, version_id: int):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        from flask import abort

        abort(404)
    version = get_version_for_month_or_404(schedule_month, version_id)
    return schedule_month, version


def _flash_error(exc) -> None:
    current_app.logger.warning("Erro de compensacao: %s", exc)
    if isinstance(exc, CompensationServiceError):
        for message in exc.errors.values() or [str(exc)]:
            flash(message, "warning")
    else:
        flash("Pedido invalido.", "warning")
