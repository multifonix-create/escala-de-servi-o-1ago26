from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.extensions import db
from app.services import ScheduleServiceError
from app.models import DiagnosticIssue, DiagnosticRun, GenerationRun, Military, ScheduleMonthStatus
from app.services.assignment_codes import ASSIGNMENT_CODE_DEFINITIONS
from app.services.assignment_service import (
    AssignmentServiceError,
    clear_assignment,
    get_assignment,
    list_changes,
    lock_assignment,
    save_manual_assignment,
    unlock_assignment,
    validate_assignment,
)
from app.services.diagnostic_service import ScheduleDiagnosticService, latest_run
from app.services.monthly_grid_builder import build_monthly_grid
from app.services.schedule_generator import ScheduleGenerationError, ScheduleGenerator, latest_generation_run
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
    generation_run = latest_generation_run(grid.version.id) if grid and grid.version else None
    return render_template(
        "schedules/month.html",
        year=year,
        month=month,
        schedule_month=schedule_month,
        grid=grid,
        generation_run=generation_run,
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
    diagnostic_run = latest_run(version.id)
    generation_run = latest_generation_run(version.id)
    diagnostic_cells = _diagnostic_cells(diagnostic_run)
    previous_year, previous_month_number = previous_month(year, month)
    next_year, next_month_number = next_month(year, month)
    return render_template(
        "schedules/month.html",
        year=year,
        month=month,
        schedule_month=schedule_month,
        grid=grid,
        selected_version=version,
        diagnostic_run=diagnostic_run,
        generation_run=generation_run,
        diagnostic_cells=diagnostic_cells,
        previous_year=previous_year,
        previous_month=previous_month_number,
        next_year=next_year,
        next_month=next_month_number,
    )


@schedules_bp.get("/<int:year>/<int:month>/versoes/<int:version_id>/geracoes")
def generation_index(year: int, month: int, version_id: int):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        abort(404)
    version = get_version_for_month_or_404(schedule_month, version_id)
    runs = (
        GenerationRun.query.filter_by(schedule_version_id=version.id)
        .order_by(GenerationRun.created_at.desc(), GenerationRun.id.desc())
        .all()
    )
    return render_template(
        "schedules/generations.html",
        schedule_month=schedule_month,
        version=version,
        runs=runs,
        can_generate=version.status == ScheduleMonthStatus.DRAFT.value,
    )


@schedules_bp.post("/<int:year>/<int:month>/versoes/<int:version_id>/gerar")
def run_generation(year: int, month: int, version_id: int):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        abort(404)
    version = get_version_for_month_or_404(schedule_month, version_id)
    try:
        generation_run = ScheduleGenerator().generate_at_po(version)
    except ScheduleGenerationError as exc:
        for message in exc.errors.values() or [str(exc)]:
            flash(message, "warning")
        return redirect(url_for("schedules.generation_index", year=year, month=month, version_id=version.id))
    flash("Geracao AT/PO concluida.", "success")
    return redirect(
        url_for(
            "schedules.generation_detail",
            year=year,
            month=month,
            version_id=version.id,
            run_id=generation_run.id,
        )
    )


@schedules_bp.get("/<int:year>/<int:month>/versoes/<int:version_id>/geracoes/<int:run_id>")
def generation_detail(year: int, month: int, version_id: int, run_id: int):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        abort(404)
    version = get_version_for_month_or_404(schedule_month, version_id)
    generation_run = db.get_or_404(GenerationRun, run_id)
    if generation_run.schedule_version_id != version.id:
        abort(404)
    details = generation_run.selection_details
    selected = [item for item in details if item.is_selected]
    excluded = [item for item in details if not item.is_eligible and item.military_id is not None]
    incomplete = [item for item in details if item.military_id is None]
    return render_template(
        "schedules/generation_detail.html",
        schedule_month=schedule_month,
        version=version,
        generation_run=generation_run,
        selected_details=selected,
        excluded_details=excluded,
        incomplete_details=incomplete,
    )


@schedules_bp.get("/<int:year>/<int:month>/versoes/<int:version_id>/diagnostico")
def diagnostic_index(year: int, month: int, version_id: int):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        abort(404)
    version = get_version_for_month_or_404(schedule_month, version_id)
    run = latest_run(version.id)
    return render_template(
        "schedules/diagnostic.html",
        schedule_month=schedule_month,
        version=version,
        run=run,
        issues=run.issues if run else [],
        selected_level=request.args.get("level", ""),
        selected_category=request.args.get("category", ""),
    )


@schedules_bp.post("/<int:year>/<int:month>/versoes/<int:version_id>/diagnostico/executar")
def run_diagnostic(year: int, month: int, version_id: int):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        abort(404)
    version = get_version_for_month_or_404(schedule_month, version_id)
    diagnostic_run = ScheduleDiagnosticService().run_and_persist(version)
    flash("Diagnostico executado.", "success")
    return redirect(
        url_for(
            "schedules.diagnostic_run_detail",
            year=year,
            month=month,
            version_id=version.id,
            run_id=diagnostic_run.id,
        )
    )


@schedules_bp.get("/<int:year>/<int:month>/versoes/<int:version_id>/diagnostico/<int:run_id>")
def diagnostic_run_detail(year: int, month: int, version_id: int, run_id: int):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        abort(404)
    version = get_version_for_month_or_404(schedule_month, version_id)
    run = db.get_or_404(DiagnosticRun, run_id)
    if run.schedule_version_id != version.id:
        abort(404)
    level = request.args.get("level", "")
    category = request.args.get("category", "")
    issues = run.issues
    if level:
        issues = [issue for issue in issues if issue.level == level]
    if category:
        issues = [issue for issue in issues if issue.category == category]
    return render_template(
        "schedules/diagnostic.html",
        schedule_month=schedule_month,
        version=version,
        run=run,
        issues=issues,
        selected_level=level,
        selected_category=category,
    )


@schedules_bp.get("/<int:year>/<int:month>/versoes/<int:version_id>/diagnostico/<int:run_id>/problemas/<int:issue_id>")
def diagnostic_issue_detail(year: int, month: int, version_id: int, run_id: int, issue_id: int):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        abort(404)
    version = get_version_for_month_or_404(schedule_month, version_id)
    issue = db.get_or_404(DiagnosticIssue, issue_id)
    if issue.diagnostic_run_id != run_id or issue.diagnostic_run.schedule_version_id != version.id:
        abort(404)
    return render_template(
        "schedules/diagnostic_issue.html",
        schedule_month=schedule_month,
        version=version,
        issue=issue,
    )


@schedules_bp.get("/<int:year>/<int:month>/versoes/<int:version_id>/militares/<int:military_id>/dias/<assignment_date>")
def edit_assignment(year: int, month: int, version_id: int, military_id: int, assignment_date: str):
    schedule_month, version, military, parsed_date = _assignment_route_context(
        year,
        month,
        version_id,
        military_id,
        assignment_date,
    )
    if parsed_date is None:
        flash("Data invalida.", "warning")
        return redirect(url_for("schedules.version_detail", year=year, month=month, version_id=version_id))

    assignment = get_assignment(version.id, military.id, parsed_date)
    current_code = assignment.code if assignment and assignment.is_visible else ""
    validation = validate_assignment(version, military, parsed_date, current_code or "DS") if current_code else None
    return render_template(
        "schedules/edit_assignment.html",
        schedule_month=schedule_month,
        version=version,
        military=military,
        assignment_date=parsed_date,
        assignment=assignment,
        validation=validation,
        codes=ASSIGNMENT_CODE_DEFINITIONS,
        errors={},
    )


@schedules_bp.post("/<int:year>/<int:month>/versoes/<int:version_id>/militares/<int:military_id>/dias/<assignment_date>")
def save_assignment(year: int, month: int, version_id: int, military_id: int, assignment_date: str):
    schedule_month, version, military, parsed_date = _assignment_route_context(
        year,
        month,
        version_id,
        military_id,
        assignment_date,
    )
    if parsed_date is None:
        flash("Data invalida.", "warning")
        return redirect(url_for("schedules.version_detail", year=year, month=month, version_id=version_id))

    override_requested = request.form.get("override_requested") == "on"
    lock_requested = request.form.get("is_locked") == "on"
    try:
        assignment, validation = save_manual_assignment(
            version,
            military,
            parsed_date,
            request.form.get("code", ""),
            notes=request.form.get("notes"),
            override_requested=override_requested,
            override_reason=request.form.get("override_reason"),
            lock_assignment=lock_requested,
        )
    except AssignmentServiceError as exc:
        for message in exc.errors.values():
            flash(message, "warning")
        return render_template(
            "schedules/edit_assignment.html",
            schedule_month=schedule_month,
            version=version,
            military=military,
            assignment_date=parsed_date,
            assignment=get_assignment(version.id, military.id, parsed_date),
            validation=None,
            codes=ASSIGNMENT_CODE_DEFINITIONS,
            errors=exc.errors,
        ), 400

    for warning in validation.warnings:
        flash(warning, "warning")
    flash("Atribuicao manual guardada.", "success")
    return redirect(
        url_for(
            "schedules.edit_assignment",
            year=year,
            month=month,
            version_id=version.id,
            military_id=military.id,
            assignment_date=parsed_date.isoformat(),
        )
    )


@schedules_bp.post("/<int:year>/<int:month>/versoes/<int:version_id>/militares/<int:military_id>/dias/<assignment_date>/limpar")
def clear_assignment_route(year: int, month: int, version_id: int, military_id: int, assignment_date: str):
    _, version, military, parsed_date = _assignment_route_context(year, month, version_id, military_id, assignment_date)
    if parsed_date is None:
        abort(404)
    assignment = get_assignment(version.id, military.id, parsed_date)
    if assignment is None:
        flash("Nao existe atribuicao manual para limpar.", "warning")
    else:
        try:
            clear_assignment(assignment, request.form.get("reason"))
        except AssignmentServiceError as exc:
            for message in exc.errors.values():
                flash(message, "warning")
        else:
            flash("Celula manual limpa.", "success")
    return redirect(url_for("schedules.edit_assignment", year=year, month=month, version_id=version.id, military_id=military.id, assignment_date=parsed_date.isoformat()))


@schedules_bp.post("/<int:year>/<int:month>/versoes/<int:version_id>/militares/<int:military_id>/dias/<assignment_date>/bloquear")
def lock_assignment_route(year: int, month: int, version_id: int, military_id: int, assignment_date: str):
    _, version, military, parsed_date = _assignment_route_context(year, month, version_id, military_id, assignment_date)
    if parsed_date is None:
        abort(404)
    assignment = get_assignment(version.id, military.id, parsed_date)
    if assignment is None:
        flash("Nao existe atribuicao manual para bloquear.", "warning")
    else:
        lock_assignment(assignment, request.form.get("reason"))
        flash("Celula bloqueada.", "success")
    return redirect(url_for("schedules.edit_assignment", year=year, month=month, version_id=version.id, military_id=military.id, assignment_date=parsed_date.isoformat()))


@schedules_bp.post("/<int:year>/<int:month>/versoes/<int:version_id>/militares/<int:military_id>/dias/<assignment_date>/desbloquear")
def unlock_assignment_route(year: int, month: int, version_id: int, military_id: int, assignment_date: str):
    _, version, military, parsed_date = _assignment_route_context(year, month, version_id, military_id, assignment_date)
    if parsed_date is None:
        abort(404)
    assignment = get_assignment(version.id, military.id, parsed_date)
    if assignment is None:
        flash("Nao existe atribuicao manual para desbloquear.", "warning")
    else:
        unlock_assignment(assignment, request.form.get("reason"))
        flash("Celula desbloqueada.", "success")
    return redirect(url_for("schedules.edit_assignment", year=year, month=month, version_id=version.id, military_id=military.id, assignment_date=parsed_date.isoformat()))


@schedules_bp.get("/<int:year>/<int:month>/versoes/<int:version_id>/militares/<int:military_id>/dias/<assignment_date>/historico")
def assignment_history(year: int, month: int, version_id: int, military_id: int, assignment_date: str):
    schedule_month, version, military, parsed_date = _assignment_route_context(year, month, version_id, military_id, assignment_date)
    if parsed_date is None:
        abort(404)
    assignment = get_assignment(version.id, military.id, parsed_date)
    changes = list_changes(assignment) if assignment else []
    return render_template(
        "schedules/assignment_history.html",
        schedule_month=schedule_month,
        version=version,
        military=military,
        assignment_date=parsed_date,
        assignment=assignment,
        changes=changes,
    )


def _assignment_route_context(year: int, month: int, version_id: int, military_id: int, assignment_date: str):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        abort(404)
    version = get_version_for_month_or_404(schedule_month, version_id)
    military = db.get_or_404(Military, military_id)
    try:
        parsed_date = date.fromisoformat(assignment_date)
    except ValueError:
        parsed_date = None
    return schedule_month, version, military, parsed_date


def _diagnostic_cells(diagnostic_run: DiagnosticRun | None) -> set[tuple[int, str]]:
    if diagnostic_run is None:
        return set()
    return {
        (issue.military_id, issue.assignment_date.isoformat())
        for issue in diagnostic_run.issues
        if issue.military_id is not None and issue.assignment_date is not None
    }
