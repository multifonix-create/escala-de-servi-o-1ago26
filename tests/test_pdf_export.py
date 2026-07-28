import re
from datetime import date

from app.extensions import db
from app.models import (
    Assignment,
    DiagnosticIssue,
    DiagnosticRun,
    FunctionalType,
    Military,
    MilitaryTeamHistory,
    ScheduleMonthStatus,
    Team,
)
from app.services.export_service import SchedulePdfExportService
from tests.test_excel_export import _export_context


def _page_count(pdf_bytes: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page\b", pdf_bytes))


def _is_a3_landscape(pdf_bytes: bytes) -> bool:
    match = re.search(rb"/MediaBox\s*\[\s*0\s+0\s+([0-9.]+)\s+([0-9.]+)\s*\]", pdf_bytes)
    if not match:
        return False
    width = float(match.group(1))
    height = float(match.group(2))
    return width > height and 1180 <= width <= 1200 and 835 <= height <= 850


def test_pdf_export_creates_a3_pdf_without_database_changes(app):
    with app.app_context():
        schedule_month, version = _export_context()
        counts_before = (
            Assignment.query.count(),
            DiagnosticRun.query.count(),
            DiagnosticIssue.query.count(),
        )

        result = SchedulePdfExportService().export_version(schedule_month, version)
        pdf_bytes = result.stream.getvalue()

        assert result.filename == "Escala_2026_01_Versao_1_Rascunho.pdf"
        assert result.mimetype == "application/pdf"
        assert pdf_bytes.startswith(b"%PDF")
        assert _is_a3_landscape(pdf_bytes)
        assert _page_count(pdf_bytes) >= 4
        assert b"Escala de Servico" in pdf_bytes
        assert b"RASCUNHO - NAO OFICIAL" in pdf_bytes
        assert b"Legenda" in pdf_bytes
        assert b"Resumo" in pdf_bytes
        assert b"Diagnostico" in pdf_bytes
        assert b"Alteracoes Manuais" in pdf_bytes
        assert b"TEST-EXPORT" in pdf_bytes
        assert b"'=Militar Exportacao" in pdf_bytes
        assert counts_before == (
            Assignment.query.count(),
            DiagnosticRun.query.count(),
            DiagnosticIssue.query.count(),
        )


def test_pdf_export_route_downloads_pdf(client, app):
    with app.app_context():
        schedule_month, version = _export_context(status=ScheduleMonthStatus.VALIDATED.value)
        url = f"/escala/{schedule_month.year}/{schedule_month.month}/versoes/{version.id}/exportar/pdf"

    response = client.get(url)

    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    assert "Escala_2026_01_Versao_1_Validada.pdf" in response.headers["Content-Disposition"]
    assert response.data.startswith(b"%PDF")
    assert b"VALIDADA - AGUARDA PUBLICACAO" in response.data


def test_pdf_export_identifies_official_published_version(app):
    with app.app_context():
        schedule_month, version = _export_context(status=ScheduleMonthStatus.PUBLISHED.value, official=True)

        pdf_bytes = SchedulePdfExportService().export_version(schedule_month, version).stream.getvalue()

        assert b"VERSAO OFICIAL" in pdf_bytes
        assert b"Versao oficial publicada" in pdf_bytes


def test_pdf_export_handles_many_rows_with_pagination(app):
    with app.app_context():
        schedule_month, version = _export_context()
        team = Team.query.filter_by(code="C").one()
        for index in range(60):
            military = Military(
                name=f"Militar PDF {index:03d}",
                nim=f"77{index:04d}",
                functional_type=FunctionalType.PATRULHEIRO.value,
                start_date=date(2026, 1, 1),
            )
            db.session.add(military)
            db.session.flush()
            db.session.add(
                MilitaryTeamHistory(
                    military_id=military.id,
                    team_id=team.id,
                    start_date=date(2026, 1, 1),
                )
            )
        db.session.commit()
        counts_before = (Military.query.count(), Assignment.query.count())

        pdf_bytes = SchedulePdfExportService().export_version(schedule_month, version).stream.getvalue()

        assert _page_count(pdf_bytes) > 4
        assert b"Militar PDF 059" in pdf_bytes
        assert counts_before == (Military.query.count(), Assignment.query.count())
