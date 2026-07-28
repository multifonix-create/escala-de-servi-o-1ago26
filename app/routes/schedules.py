from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.services import ScheduleServiceError
from app.services.monthly_grid_builder import build_monthly_grid
from app.services.schedule_service import (
    create_schedule_month,
    current_month,
    get_schedule_month,
    get_version_for_month_or_404,
    list_schedule_months,
    list_versions,
    next_month,
    previous_month,
)
from app.validators import validate_schedule_month_payload, validate_schedule_month_path


schedules_bp = Blueprint("schedules", __name__, url_prefix="/escala")


@schedules_bp.get("")
def index():
    validation = validate_schedule_month_payload(request.args)
    if request.args and validation.is_valid:
        return redirect(
            url_for(
                "schedules.month_detail",
                year=validation.year,
                month=validation.month,
            )
        )
    year, month = current_month()
    return render_template(
        "schedules/index.html",
        year=year,
        month=month,
        schedule_months=list_schedule_months(),
        errors=validation.errors if request.args else {},
    )


@schedules_bp.get("/<int:year>/<int:month>")
def month_detail(year: int, month: int):
    validation = validate_schedule_month_path(year, month)
    if not validation.is_valid:
        flash("Mes ou ano invalido.", "warning")
        return redirect(url_for("schedules.index"))

    schedule_month = get_schedule_month(year, month)
    previous_year, previous_month_number = previous_month(year, month)
    next_year, next_month_number = next_month(year, month)
    grid = build_monthly_grid(schedule_month) if schedule_month else None
    return render_template(
        "schedules/month.html",
        year=year,
        month=month,
        schedule_month=schedule_month,
        grid=grid,
        previous_year=previous_year,
        previous_month=previous_month_number,
        next_year=next_year,
        next_month=next_month_number,
    )


@schedules_bp.post("/<int:year>/<int:month>/criar")
def create_month(year: int, month: int):
    try:
        create_schedule_month(year, month)
    except ScheduleServiceError as exc:
        for message in exc.errors.values():
            flash(message, "warning")
    else:
        flash("Mes de escala criado em rascunho.", "success")
    return redirect(url_for("schedules.month_detail", year=year, month=month))


@schedules_bp.get("/<int:year>/<int:month>/versoes")
def versions(year: int, month: int):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        flash("Mes de escala inexistente.", "warning")
        return redirect(url_for("schedules.month_detail", year=year, month=month))
    return render_template(
        "schedules/versions.html",
        schedule_month=schedule_month,
        versions=list_versions(schedule_month.id),
    )


@schedules_bp.get("/<int:year>/<int:month>/versoes/<int:version_id>")
def version_detail(year: int, month: int, version_id: int):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        flash("Mes de escala inexistente.", "warning")
        return redirect(url_for("schedules.month_detail", year=year, month=month))
    version = get_version_for_month_or_404(schedule_month, version_id)
    grid = build_monthly_grid(schedule_month, version=version)
    previous_year, previous_month_number = previous_month(year, month)
    next_year, next_month_number = next_month(year, month)
    return render_template(
        "schedules/month.html",
        year=year,
        month=month,
        schedule_month=schedule_month,
        grid=grid,
        selected_version=version,
        previous_year=previous_year,
        previous_month=previous_month_number,
        next_year=next_year,
        next_month=next_month_number,
    )
