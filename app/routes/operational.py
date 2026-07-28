from datetime import date

import click
from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.extensions import db
from app.models import OperationalTestDecision, ScheduleVersion, Team
from app.services.cycle_calculator import CycleCalculationError
from app.services.operational_import_service import (
    OperationalImportError,
    import_military_data,
    preview_military_import,
)
from app.services.operational_readiness_service import (
    build_cycle_conference,
    evaluate_operational_readiness,
)
from app.services.operational_test_service import (
    OperationalTestError,
    archive_operational_test,
    create_operational_test_version,
    evaluate_operational_test,
)


operational_bp = Blueprint("operational", __name__, url_prefix="/controlo-operacional")


@operational_bp.get("")
def dashboard():
    return render_template(
        "operational/dashboard.html",
        report=evaluate_operational_readiness(),
    )


@operational_bp.route("/importacao", methods=["GET", "POST"])
def import_page():
    preview = None
    report = None
    path_value = request.form.get("csv_path", "") if request.method == "POST" else ""
    if request.method == "POST":
        try:
            if request.form.get("action") == "import":
                report = import_military_data(path_value, confirm=request.form.get("confirm_import") == "on")
                flash("Importacao operacional concluida.", "success")
            else:
                preview = preview_military_import(path_value)
        except OperationalImportError as exc:
            for message in exc.errors or [str(exc)]:
                flash(message, "warning")
    return render_template(
        "operational/import.html",
        preview=preview,
        report=report,
        csv_path=path_value,
    )


@operational_bp.route("/teste/criar", methods=["GET", "POST"])
def create_test():
    errors = {}
    if request.method == "POST":
        year = _parse_int(request.form.get("year"))
        month = _parse_int(request.form.get("month"))
        if year is None or month is None:
            errors["month"] = "Indique ano e mes validos."
        else:
            try:
                version = create_operational_test_version(year, month, request.form.get("notes"))
            except Exception as exc:
                errors["version"] = str(exc)
            else:
                flash("Versao de teste operacional criada.", "success")
                return redirect(
                    url_for(
                        "schedules.version_detail",
                        year=version.schedule_month.year,
                        month=version.schedule_month.month,
                        version_id=version.id,
                    )
                )
    today = date.today()
    return render_template("operational/create_test.html", year=today.year, month=today.month, errors=errors)


@operational_bp.post("/teste/<int:version_id>/arquivar")
def archive_test(version_id: int):
    version = db.get_or_404(ScheduleVersion, version_id)
    try:
        archive_operational_test(version, request.form.get("reason"))
    except OperationalTestError as exc:
        for message in exc.errors.values() or [str(exc)]:
            flash(message, "warning")
    else:
        flash("Teste operacional arquivado.", "success")
    return redirect(url_for("operational.dashboard"))


@operational_bp.route("/teste/<int:version_id>/avaliar", methods=["GET", "POST"])
def evaluate_test(version_id: int):
    version = db.get_or_404(ScheduleVersion, version_id)
    errors = {}
    if request.method == "POST":
        try:
            evaluate_operational_test(
                version,
                request.form.get("decision", ""),
                request.form.get("notes"),
            )
        except OperationalTestError as exc:
            errors = exc.errors
            for message in exc.errors.values() or [str(exc)]:
                flash(message, "warning")
        else:
            flash("Avaliacao do teste operacional guardada.", "success")
            return redirect(url_for("operational.dashboard"))
    return render_template(
        "operational/evaluate.html",
        version=version,
        decisions=OperationalTestDecision,
        errors=errors,
    )


@operational_bp.get("/ciclo")
def cycle_conference():
    teams = Team.query.order_by(Team.code.asc()).all()
    selected_team = None
    days = []
    errors = {}
    team_id = _parse_int(request.args.get("team_id"))
    start = _parse_date(request.args.get("start_date"))
    end = _parse_date(request.args.get("end_date"))
    if team_id:
        selected_team = db.session.get(Team, team_id)
    if selected_team and start and end:
        try:
            days = build_cycle_conference(selected_team, start, end)
        except CycleCalculationError as exc:
            errors = exc.errors
    return render_template(
        "operational/cycle.html",
        teams=teams,
        selected_team=selected_team,
        days=days,
        errors=errors,
        start_date=request.args.get("start_date", ""),
        end_date=request.args.get("end_date", ""),
    )


def register_cli(app):
    @app.cli.command("validate-real-data")
    def validate_real_data_command():
        report = evaluate_operational_readiness()
        click.echo(f"Estado: {report.status}")
        click.echo(f"Militares ativos: {report.counts['active_militaries']}")
        for issue in report.issues:
            click.echo(f"{issue.level} {issue.code}: {issue.message}")

    @app.cli.command("preview-military-import")
    @click.argument("csv_path")
    def preview_military_import_command(csv_path):
        preview = preview_military_import(csv_path)
        click.echo(_preview_text(preview))

    @app.cli.command("import-military-data")
    @click.argument("csv_path")
    @click.option("--confirm", is_flag=True, help="Confirma a escrita na base real apos pre-visualizacao valida.")
    def import_military_data_command(csv_path, confirm):
        if not confirm:
            preview = preview_military_import(csv_path)
            click.echo(_preview_text(preview))
            click.echo("Sem --confirm, nenhuma alteracao foi feita.")
            return
        report = import_military_data(csv_path, confirm=True)
        click.echo(f"Backup: {report.backup.path}")
        click.echo(f"Criados: {report.created}")
        click.echo(f"Atualizados: {report.updated}")
        click.echo(f"Ignorados: {report.ignored}")
        click.echo(f"Rejeitados: {report.rejected}")
        click.echo(f"Totais finais: {report.final_totals}")


def _preview_text(preview) -> str:
    lines = [
        f"Ficheiro: {preview.path}",
        f"Total: {preview.total_rows}",
        f"Validas: {preview.valid_rows}",
        f"Invalidas: {preview.invalid_rows}",
        f"Existentes: {preview.existing_rows}",
        f"Pode importar: {'sim' if preview.can_import else 'nao'}",
    ]
    lines.extend(f"Bloqueio: {blocker}" for blocker in preview.blockers)
    lines.extend(f"Aviso: {warning}" for warning in preview.warnings)
    return "\n".join(lines)


def _parse_int(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except ValueError:
        return None


def _parse_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None
