from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.extensions import db
from app.models import (
    Holiday,
    HolidayLeaveCredit,
    HOLIDAY_LEAVE_CREDIT_STATUS_LABELS,
    HOLIDAY_SCOPE_LABELS,
    ScheduleMonthStatus,
)
from app.services.holiday_credit_service import (
    HolidayCreditServiceError,
    balance_by_military,
    cancel_credit_right,
    cancel_schedule,
    confirm_credit_used,
    create_credit_from_assignment,
    create_holiday,
    list_credits,
    list_holidays,
    list_potential_credits,
    reschedule_credit,
    schedule_credit,
    set_holiday_active,
    update_holiday,
)
from app.services.schedule_service import get_schedule_month, get_version_for_month_or_404, list_versions


holidays_bp = Blueprint("holidays", __name__)


@holidays_bp.get("/feriados")
def list_holidays_route():
    return render_template(
        "holidays/list.html",
        holidays=list_holidays(include_inactive=True),
        scope_labels=HOLIDAY_SCOPE_LABELS,
    )


@holidays_bp.route("/feriados/novo", methods=["GET", "POST"])
def create_holiday_route():
    if request.method == "POST":
        try:
            create_holiday(request.form)
        except HolidayCreditServiceError as exc:
            for message in exc.errors.values() or [str(exc)]:
                flash(message, "warning")
            return render_template(
                "holidays/form.html",
                holiday=None,
                scope_labels=HOLIDAY_SCOPE_LABELS,
                errors=exc.errors,
            ), 400
        flash("Feriado criado.", "success")
        return redirect(url_for("holidays.list_holidays_route"))
    return render_template(
        "holidays/form.html",
        holiday=None,
        scope_labels=HOLIDAY_SCOPE_LABELS,
        errors={},
    )


@holidays_bp.route("/feriados/<int:holiday_id>/editar", methods=["GET", "POST"])
def edit_holiday_route(holiday_id: int):
    holiday = db.get_or_404(Holiday, holiday_id)
    if request.method == "POST":
        try:
            update_holiday(holiday, request.form)
        except HolidayCreditServiceError as exc:
            for message in exc.errors.values() or [str(exc)]:
                flash(message, "warning")
            return render_template(
                "holidays/form.html",
                holiday=holiday,
                scope_labels=HOLIDAY_SCOPE_LABELS,
                errors=exc.errors,
            ), 400
        flash("Feriado atualizado.", "success")
        return redirect(url_for("holidays.list_holidays_route"))
    return render_template(
        "holidays/form.html",
        holiday=holiday,
        scope_labels=HOLIDAY_SCOPE_LABELS,
        errors={},
    )


@holidays_bp.post("/feriados/<int:holiday_id>/ativar")
def activate_holiday_route(holiday_id: int):
    set_holiday_active(db.get_or_404(Holiday, holiday_id), True)
    flash("Feriado ativado.", "success")
    return redirect(url_for("holidays.list_holidays_route"))


@holidays_bp.post("/feriados/<int:holiday_id>/desativar")
def deactivate_holiday_route(holiday_id: int):
    set_holiday_active(db.get_or_404(Holiday, holiday_id), False)
    flash("Feriado desativado. Creditos existentes permanecem preservados.", "success")
    return redirect(url_for("holidays.list_holidays_route"))


@holidays_bp.get("/ff")
def credits_index():
    status = request.args.get("status") or None
    return render_template(
        "ff/list.html",
        credits=list_credits(status=status),
        balances=balance_by_military(),
        status_labels=HOLIDAY_LEAVE_CREDIT_STATUS_LABELS,
        selected_status=status or "",
    )


@holidays_bp.get("/ff/<int:credit_id>")
def credit_detail(credit_id: int):
    credit = db.get_or_404(HolidayLeaveCredit, credit_id)
    return render_template("ff/detail.html", credit=credit, status_labels=HOLIDAY_LEAVE_CREDIT_STATUS_LABELS)


@holidays_bp.route("/ff/<int:credit_id>/agendar", methods=["GET", "POST"])
def schedule_credit_route(credit_id: int):
    credit = db.get_or_404(HolidayLeaveCredit, credit_id)
    if request.method == "POST":
        try:
            schedule_credit(
                credit,
                _schedule_version_from_form(),
                date.fromisoformat(request.form.get("scheduled_date", "")),
                notes=request.form.get("notes"),
            )
        except (HolidayCreditServiceError, ValueError) as exc:
            _flash_error(exc)
            return _schedule_template(credit, "ff/schedule.html", 400)
        flash("FF agendada.", "success")
        return redirect(url_for("holidays.credit_detail", credit_id=credit.id))
    return _schedule_template(credit, "ff/schedule.html")


@holidays_bp.route("/ff/<int:credit_id>/reagendar", methods=["GET", "POST"])
def reschedule_credit_route(credit_id: int):
    credit = db.get_or_404(HolidayLeaveCredit, credit_id)
    if request.method == "POST":
        try:
            reschedule_credit(
                credit,
                _schedule_version_from_form(),
                date.fromisoformat(request.form.get("scheduled_date", "")),
                notes=request.form.get("notes"),
            )
        except (HolidayCreditServiceError, ValueError) as exc:
            _flash_error(exc)
            return _schedule_template(credit, "ff/schedule.html", 400)
        flash("FF reagendada.", "success")
        return redirect(url_for("holidays.credit_detail", credit_id=credit.id))
    return _schedule_template(credit, "ff/schedule.html")


@holidays_bp.post("/ff/<int:credit_id>/cancelar-agendamento")
def cancel_schedule_route(credit_id: int):
    credit = db.get_or_404(HolidayLeaveCredit, credit_id)
    try:
        cancel_schedule(credit, request.form.get("reason"))
    except HolidayCreditServiceError as exc:
        _flash_error(exc)
    else:
        flash("Agendamento de FF cancelado.", "success")
    return redirect(url_for("holidays.credit_detail", credit_id=credit.id))


@holidays_bp.post("/ff/<int:credit_id>/confirmar-gozo")
def confirm_used_route(credit_id: int):
    credit = db.get_or_404(HolidayLeaveCredit, credit_id)
    try:
        confirm_credit_used(credit, request.form.get("description"))
    except HolidayCreditServiceError as exc:
        _flash_error(exc)
    else:
        flash("Gozo de FF confirmado.", "success")
    return redirect(url_for("holidays.credit_detail", credit_id=credit.id))


@holidays_bp.post("/ff/<int:credit_id>/cancelar-direito")
def cancel_right_route(credit_id: int):
    credit = db.get_or_404(HolidayLeaveCredit, credit_id)
    try:
        cancel_credit_right(credit, request.form.get("reason"))
    except HolidayCreditServiceError as exc:
        _flash_error(exc)
    else:
        flash("Direito FF cancelado.", "success")
    return redirect(url_for("holidays.credit_detail", credit_id=credit.id))


@holidays_bp.get("/ff/<int:credit_id>/historico")
def credit_history(credit_id: int):
    credit = db.get_or_404(HolidayLeaveCredit, credit_id)
    return render_template("ff/history.html", credit=credit)


@holidays_bp.get("/escala/<int:year>/<int:month>/versoes/<int:version_id>/ff/processar")
def process_ff_candidates(year: int, month: int, version_id: int):
    schedule_month, version = _version_context(year, month, version_id)
    return render_template(
        "ff/process.html",
        schedule_month=schedule_month,
        version=version,
        candidates=list_potential_credits(version),
        can_process=version.status in FF_SOURCE_VERSION_STATUSES or version.status == ScheduleMonthStatus.DRAFT.value,
    )


@holidays_bp.post("/escala/<int:year>/<int:month>/versoes/<int:version_id>/ff/processar")
def create_ff_candidates(year: int, month: int, version_id: int):
    schedule_month, version = _version_context(year, month, version_id)
    created = 0
    if version.status == ScheduleMonthStatus.DRAFT.value and request.form.get("confirm_service_performed") != "on":
        flash("Confirme explicitamente que os servicos em feriado foram prestados.", "warning")
        return redirect(url_for("holidays.process_ff_candidates", year=year, month=month, version_id=version.id))
    selected_assignment_ids = {int(value) for value in request.form.getlist("assignment_id") if value.isdigit()}
    for candidate in list_potential_credits(version):
        if candidate.assignment.id not in selected_assignment_ids or candidate.existing_credit is not None:
            continue
        try:
            create_credit_from_assignment(
                candidate.assignment,
                candidate.holiday,
                manual_confirmation=request.form.get("confirm_service_performed") == "on",
            )
        except HolidayCreditServiceError as exc:
            _flash_error(exc)
        else:
            created += 1
    flash(f"Creditos FF criados: {created}.", "success")
    return redirect(url_for("holidays.process_ff_candidates", year=year, month=month, version_id=version.id))


def _schedule_template(credit: HolidayLeaveCredit, template: str, status_code: int = 200):
    versions = [
        version
        for version in list_versions(credit.source_schedule_version.schedule_month.id)
        if version.status == ScheduleMonthStatus.DRAFT.value
    ]
    response = render_template(
        template,
        credit=credit,
        versions=versions,
        status_labels=HOLIDAY_LEAVE_CREDIT_STATUS_LABELS,
    )
    return (response, status_code) if status_code != 200 else response


def _schedule_version_from_form():
    version_id = request.form.get("schedule_version_id")
    if not version_id or not version_id.isdigit():
        raise HolidayCreditServiceError("Versao invalida.", {"schedule_version": "Escolha uma versao DRAFT."})
    from app.models import ScheduleVersion

    version = db.session.get(ScheduleVersion, int(version_id))
    if version is None:
        raise HolidayCreditServiceError("Versao inexistente.", {"schedule_version": "Escolha uma versao DRAFT."})
    return version


def _version_context(year: int, month: int, version_id: int):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        abort(404)
    version = get_version_for_month_or_404(schedule_month, version_id)
    return schedule_month, version


def _flash_error(exc) -> None:
    if isinstance(exc, HolidayCreditServiceError):
        for message in exc.errors.values() or [str(exc)]:
            flash(message, "warning")
    else:
        flash("Pedido invalido.", "warning")


FF_SOURCE_VERSION_STATUSES = {
    ScheduleMonthStatus.VALIDATED.value,
    ScheduleMonthStatus.PUBLISHED.value,
    ScheduleMonthStatus.CLOSED.value,
}
