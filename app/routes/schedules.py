import json
from datetime import date, time

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from app.extensions import db
from app.services import ScheduleServiceError
from app.models import Assignment, AssignmentSource, DiagnosticIssue, DiagnosticRun, GenerationRun, Military, ScheduleMonthStatus, ScheduleVersionStateEvent
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
from app.services.compensation_service import CompensationMaintenanceService
from app.services.monthly_grid_builder import build_monthly_grid
from app.services.schedule_generator import PTGenerationOptions, ScheduleGenerationError, ScheduleGenerator, latest_generation_run
from app.services.schedule_regeneration import (
    ScheduleRegenerationError,
    ScheduleRegenerationService,
    compare_versions,
)
from app.services.schedule_version_policy import ScheduleVersionPolicy
from app.services.schedule_version_workflow import ScheduleVersionWorkflow, ScheduleWorkflowError
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
    CompensationMaintenanceService().process()
    previous_year, previous_month_number = previous_month(year, month)
    next_year, next_month_number = next_month(year, month)
    grid = build_monthly_grid(schedule_month) if schedule_month else None
    generation_run = latest_generation_run(grid.version.id) if grid and grid.version else None
    version_permissions = ScheduleVersionPolicy(grid.version).as_dict() if grid and grid.version else {}
    return render_template(
        "schedules/month.html",
        year=year,
        month=month,
        schedule_month=schedule_month,
        grid=grid,
        generation_run=generation_run,
        version_permissions=version_permissions,
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
    CompensationMaintenanceService().process()
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
        version_permissions=ScheduleVersionPolicy(version).as_dict(),
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
        manual_count=_assignment_count(version.id, AssignmentSource.MANUAL.value),
        system_count=_assignment_count(version.id, AssignmentSource.SYSTEM.value),
    )


@schedules_bp.post("/<int:year>/<int:month>/versoes/<int:version_id>/gerar")
def run_generation(year: int, month: int, version_id: int):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        abort(404)
    version = get_version_for_month_or_404(schedule_month, version_id)
    try:
        generation_run = ScheduleGenerator().generate_at_po(version, pt_options=_pt_options_from_form())
    except ScheduleGenerationError as exc:
        for message in exc.errors.values() or [str(exc)]:
            flash(message, "warning")
        return redirect(url_for("schedules.generation_index", year=year, month=month, version_id=version.id))
    flash("Geracao concluida.", "success")
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
    selected_at_po = [item for item in selected if item.service_code != "PT"]
    selected_pt = [item for item in selected if item.service_code == "PT"]
    excluded = [item for item in details if not item.is_eligible and item.military_id is not None]
    incomplete = [item for item in details if item.military_id is None]
    return render_template(
        "schedules/generation_detail.html",
        schedule_month=schedule_month,
        version=version,
        generation_run=generation_run,
        selected_details=selected,
        selected_at_po_details=selected_at_po,
        selected_pt_details=selected_pt,
        excluded_details=excluded,
        incomplete_details=incomplete,
        summary=_json_dict(generation_run.summary_json),
    )


@schedules_bp.get("/<int:year>/<int:month>/versoes/<int:version_id>/regenerar")
def regeneration_confirm(year: int, month: int, version_id: int):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        abort(404)
    version = get_version_for_month_or_404(schedule_month, version_id)
    return render_template(
        "schedules/regenerate.html",
        schedule_month=schedule_month,
        version=version,
        manual_count=_assignment_count(version.id, AssignmentSource.MANUAL.value),
        system_count=_assignment_count(version.id, AssignmentSource.SYSTEM.value),
        imported_count=_assignment_count(version.id, AssignmentSource.IMPORTED.value),
        can_regenerate=version.status in {ScheduleMonthStatus.DRAFT.value, ScheduleMonthStatus.VALIDATED.value},
    )


@schedules_bp.post("/<int:year>/<int:month>/versoes/<int:version_id>/regenerar")
def run_regeneration(year: int, month: int, version_id: int):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        abort(404)
    version = get_version_for_month_or_404(schedule_month, version_id)
    if request.form.get("confirm_regeneration") != "on":
        flash("Confirme explicitamente a criacao de nova versao antes de regenerar.", "warning")
        return redirect(url_for("schedules.regeneration_confirm", year=year, month=month, version_id=version.id))
    try:
        summary = ScheduleRegenerationService().regenerate_automatic_at_po(version, pt_options=_pt_options_from_form())
    except ScheduleGenerationError as exc:
        for message in exc.errors.values() or [str(exc)]:
            flash(message, "warning")
        return redirect(url_for("schedules.regeneration_confirm", year=year, month=month, version_id=version.id))
    except ScheduleRegenerationError as exc:
        for message in exc.errors.values() or [str(exc)]:
            flash(message, "warning")
        return redirect(url_for("schedules.regeneration_confirm", year=year, month=month, version_id=version.id))
    flash("Regeneracao AT/PO concluida numa nova versao.", "success")
    return redirect(
        url_for(
            "schedules.compare_versions_route",
            year=year,
            month=month,
            version_id=summary.source_version_id,
            other_version_id=summary.result_version_id,
        )
    )


@schedules_bp.get("/<int:year>/<int:month>/versoes/<int:version_id>/comparar/<int:other_version_id>")
def compare_versions_route(year: int, month: int, version_id: int, other_version_id: int):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        abort(404)
    source_version = get_version_for_month_or_404(schedule_month, version_id)
    result_version = get_version_for_month_or_404(schedule_month, other_version_id)
    comparison = compare_versions(source_version, result_version)
    return render_template(
        "schedules/version_compare.html",
        schedule_month=schedule_month,
        source_version=source_version,
        result_version=result_version,
        comparison=comparison,
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


@schedules_bp.get("/<int:year>/<int:month>/versoes/<int:version_id>/validar")
def validate_version_confirm(year: int, month: int, version_id: int):
    schedule_month, version = _version_route_context(year, month, version_id)
    return render_template("schedules/validate.html", schedule_month=schedule_month, version=version, errors={}, blockers=[], warnings=[], run=None)


@schedules_bp.post("/<int:year>/<int:month>/versoes/<int:version_id>/validar")
def validate_version_action(year: int, month: int, version_id: int):
    schedule_month, version = _version_route_context(year, month, version_id)
    try:
        run = ScheduleVersionWorkflow().validate_version(
            version,
            confirm_warnings=request.form.get("confirm_warnings") == "on",
            notes=request.form.get("notes"),
        )
    except ScheduleWorkflowError as exc:
        for message in exc.errors.values() or [exc.message]:
            flash(message, "warning")
        return render_template(
            "schedules/validate.html",
            schedule_month=schedule_month,
            version=version,
            errors=exc.errors,
            blockers=exc.blockers,
            warnings=exc.warnings,
            run=exc.diagnostic_run,
        ), 400
    flash("Escala validada.", "success")
    return redirect(url_for("schedules.diagnostic_run_detail", year=year, month=month, version_id=version.id, run_id=run.id))


@schedules_bp.get("/<int:year>/<int:month>/versoes/<int:version_id>/revogar-validacao")
def revoke_validation_confirm(year: int, month: int, version_id: int):
    schedule_month, version = _version_route_context(year, month, version_id)
    return render_template("schedules/revoke_validation.html", schedule_month=schedule_month, version=version, errors={})


@schedules_bp.post("/<int:year>/<int:month>/versoes/<int:version_id>/revogar-validacao")
def revoke_validation_action(year: int, month: int, version_id: int):
    schedule_month, version = _version_route_context(year, month, version_id)
    try:
        ScheduleVersionWorkflow().revoke_validation(version, request.form.get("reason"), request.form.get("notes"))
    except ScheduleWorkflowError as exc:
        for message in exc.errors.values() or [exc.message]:
            flash(message, "warning")
        return render_template("schedules/revoke_validation.html", schedule_month=schedule_month, version=version, errors=exc.errors), 400
    flash("Validacao revogada. A versao voltou a DRAFT.", "success")
    return redirect(url_for("schedules.version_detail", year=year, month=month, version_id=version.id))


@schedules_bp.get("/<int:year>/<int:month>/versoes/<int:version_id>/publicar")
def publish_version_confirm(year: int, month: int, version_id: int):
    schedule_month, version = _version_route_context(year, month, version_id)
    current_published = schedule_month.published_version
    return render_template("schedules/publish.html", schedule_month=schedule_month, version=version, current_published=current_published, errors={})


@schedules_bp.post("/<int:year>/<int:month>/versoes/<int:version_id>/publicar")
def publish_version_action(year: int, month: int, version_id: int):
    schedule_month, version = _version_route_context(year, month, version_id)
    try:
        ScheduleVersionWorkflow().publish_version(
            version,
            confirm_replace=request.form.get("confirm_replace") == "on",
            notes=request.form.get("notes"),
        )
    except ScheduleWorkflowError as exc:
        for message in exc.errors.values() or [exc.message]:
            flash(message, "warning")
        return render_template("schedules/publish.html", schedule_month=schedule_month, version=version, current_published=schedule_month.published_version, errors=exc.errors), 400
    flash("Escala publicada.", "success")
    return redirect(url_for("schedules.version_detail", year=year, month=month, version_id=version.id))


@schedules_bp.get("/<int:year>/<int:month>/versoes/<int:version_id>/encerrar")
def close_version_confirm(year: int, month: int, version_id: int):
    schedule_month, version = _version_route_context(year, month, version_id)
    return render_template("schedules/close.html", schedule_month=schedule_month, version=version, errors={}, blockers=[], warnings=[], run=None)


@schedules_bp.post("/<int:year>/<int:month>/versoes/<int:version_id>/encerrar")
def close_version_action(year: int, month: int, version_id: int):
    schedule_month, version = _version_route_context(year, month, version_id)
    try:
        run = ScheduleVersionWorkflow().close_version(
            version,
            confirm_early=request.form.get("confirm_early") == "on",
            reason=request.form.get("reason"),
            notes=request.form.get("notes"),
        )
    except ScheduleWorkflowError as exc:
        for message in exc.errors.values() or [exc.message]:
            flash(message, "warning")
        return render_template(
            "schedules/close.html",
            schedule_month=schedule_month,
            version=version,
            errors=exc.errors,
            blockers=exc.blockers,
            warnings=exc.warnings,
            run=exc.diagnostic_run,
        ), 400
    flash("Escala encerrada.", "success")
    return redirect(url_for("schedules.diagnostic_run_detail", year=year, month=month, version_id=version.id, run_id=run.id))


@schedules_bp.get("/<int:year>/<int:month>/versoes/<int:version_id>/criar-correcao")
def correction_version_confirm(year: int, month: int, version_id: int):
    schedule_month, version = _version_route_context(year, month, version_id)
    return render_template("schedules/correction.html", schedule_month=schedule_month, version=version, errors={})


@schedules_bp.post("/<int:year>/<int:month>/versoes/<int:version_id>/criar-correcao")
def correction_version_action(year: int, month: int, version_id: int):
    schedule_month, version = _version_route_context(year, month, version_id)
    try:
        correction = ScheduleVersionWorkflow().create_correction_version(version, request.form.get("reason"), request.form.get("notes"))
    except ScheduleWorkflowError as exc:
        for message in exc.errors.values() or [exc.message]:
            flash(message, "warning")
        return render_template("schedules/correction.html", schedule_month=schedule_month, version=version, errors=exc.errors), 400
    flash("Versao de correcao criada em DRAFT.", "success")
    return redirect(url_for("schedules.version_detail", year=year, month=month, version_id=correction.id))


@schedules_bp.get("/<int:year>/<int:month>/versoes/<int:version_id>/historico-estado")
def state_history(year: int, month: int, version_id: int):
    schedule_month, version = _version_route_context(year, month, version_id)
    events = (
        ScheduleVersionStateEvent.query.filter_by(schedule_version_id=version.id)
        .order_by(ScheduleVersionStateEvent.created_at.asc(), ScheduleVersionStateEvent.id.asc())
        .all()
    )
    return render_template("schedules/state_history.html", schedule_month=schedule_month, version=version, events=events)


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


def _version_route_context(year: int, month: int, version_id: int):
    schedule_month = get_schedule_month(year, month)
    if schedule_month is None:
        abort(404)
    version = get_version_for_month_or_404(schedule_month, version_id)
    return schedule_month, version


def _diagnostic_cells(diagnostic_run: DiagnosticRun | None) -> set[tuple[int, str]]:
    if diagnostic_run is None:
        return set()
    return {
        (issue.military_id, issue.assignment_date.isoformat())
        for issue in diagnostic_run.issues
        if issue.military_id is not None and issue.assignment_date is not None
    }


def _assignment_count(version_id: int, source: str) -> int:
    return Assignment.query.filter_by(
        schedule_version_id=version_id,
        source=source,
        is_cleared=False,
    ).count()


def _pt_options_from_form() -> PTGenerationOptions:
    enabled = request.form.get("generate_pt") == "on"
    if not enabled:
        return PTGenerationOptions(enabled=False)
    duration_hours = _optional_int(request.form.get("pt_duration_hours"))
    max_daily = _optional_int(request.form.get("pt_max_daily"), default=0)
    weekdays = tuple(sorted(_optional_int(value) for value in request.form.getlist("pt_weekdays") if _optional_int(value) is not None))
    return PTGenerationOptions(
        enabled=True,
        duration_hours=duration_hours,
        start_time=_parse_time(request.form.get("pt_start_time")),
        max_daily=max_daily or 0,
        weekdays=weekdays,
        allow_support_groups=request.form.get("pt_allow_support_groups") == "on",
        policy_note=(request.form.get("pt_policy_note") or "").strip() or None,
    )


def _optional_int(value: str | None, default: int | None = None) -> int | None:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_time(value: str | None) -> time | None:
    if not value:
        return None
    try:
        return time.fromisoformat(value)
    except ValueError:
        return None


def _json_dict(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
