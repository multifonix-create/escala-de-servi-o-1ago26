from datetime import date

import pytest

from app.extensions import db
from app.models import (
    Assignment,
    AssignmentSource,
    FunctionalType,
    Military,
    OperationalTestDecision,
    ScheduleMonth,
    ScheduleMonthStatus,
    ScheduleVersion,
    Team,
    TeamCycleReference,
)
from app.services.export_service import ScheduleExcelExportService, SchedulePdfExportService
from app.services.operational_import_service import import_military_data, preview_military_import
from app.services.operational_readiness_service import READINESS_NOT_READY, evaluate_operational_readiness
from app.services.operational_test_service import (
    archive_operational_test,
    create_operational_test_version,
    evaluate_operational_test,
)
from app.services.schedule_version_policy import ScheduleVersionPolicy
from app.services.schedule_version_workflow import ScheduleVersionWorkflow, ScheduleWorkflowError


def test_operational_dashboard_reports_not_ready_without_real_data(client):
    response = client.get("/controlo-operacional")

    assert response.status_code == 200
    assert b"Nao preparado" in response.data


def test_readiness_requires_patrols_and_cycle_references(app):
    with app.app_context():
        report = evaluate_operational_readiness(today=date(2026, 1, 1))

    assert report.status == READINESS_NOT_READY
    assert any(issue.code == "NO-ACTIVE-PATROLS" for issue in report.issues)


def test_preview_military_import_validates_without_writing(tmp_path, app):
    csv_path = tmp_path / "militares.csv"
    csv_path.write_text(
        "nim,nome,tipo_funcional,equipa,ativo,data_inicio,data_fim,apto_cr,notas\n"
        "900001,Operacional Um,PATRULHEIRO,A,sim,2026-01-01,,,\n",
        encoding="utf-8",
    )
    with app.app_context():
        preview = preview_military_import(csv_path)

        assert preview.can_import
        assert preview.valid_rows == 1
        assert Military.query.count() == 0


def test_import_military_data_requires_confirmation(tmp_path, app):
    csv_path = tmp_path / "militares.csv"
    csv_path.write_text(
        "nim,nome,tipo_funcional,equipa,ativo,data_inicio,data_fim,apto_cr,notas\n"
        "900002,Operacional Dois,PATRULHEIRO,A,sim,2026-01-01,,,\n",
        encoding="utf-8",
    )
    with app.app_context(), pytest.raises(Exception):
        import_military_data(csv_path, confirm=False)


def test_import_military_data_is_idempotent_with_backup(monkeypatch, tmp_path, app):
    csv_path = tmp_path / "militares.csv"
    csv_path.write_text(
        "nim,nome,tipo_funcional,equipa,ativo,data_inicio,data_fim,apto_cr,notas\n"
        "900003,Operacional Tres,PATRULHEIRO,A,sim,2026-01-01,,,\n",
        encoding="utf-8",
    )

    class Backup:
        path = tmp_path / "backup.db"
        size_bytes = 1
        created_at = None

    monkeypatch.setattr(
        "app.services.operational_import_service.create_database_backup",
        lambda label: Backup(),
    )
    with app.app_context():
        first = import_military_data(csv_path, confirm=True)
        second = import_military_data(csv_path, confirm=True)

        assert first.created == 1
        assert second.ignored == 1
        assert Military.query.count() == 1
        assert Military.query.one().current_team.code == "A"


def test_operational_test_version_cannot_be_published(app):
    with app.app_context():
        version = create_operational_test_version(2026, 2, "Afericao local")
        version.status = ScheduleMonthStatus.VALIDATED.value
        version.validated_revision = version.content_revision
        version.validated_at = date(2026, 1, 1)
        db.session.commit()

        assert not ScheduleVersionPolicy(version).can_publish()
        with pytest.raises(ScheduleWorkflowError):
            ScheduleVersionWorkflow().publish_version(version)


def test_operational_test_archive_and_evaluation(app):
    with app.app_context():
        version = create_operational_test_version(2026, 3, "Afericao local")
        evaluation = evaluate_operational_test(
            version,
            OperationalTestDecision.REJECTED.value,
            "Sem dados suficientes.",
        )

        assert evaluation.decision == OperationalTestDecision.REJECTED.value
        archive_operational_test(version, "Fim do teste local.")
        assert version.is_archived
        assert not ScheduleVersionPolicy(version).can_generate()


def test_operational_test_exports_include_marker(app):
    with app.app_context():
        schedule_month = ScheduleMonth(year=2026, month=4, status=ScheduleMonthStatus.DRAFT.value)
        version = ScheduleVersion(
            schedule_month=schedule_month,
            version_number=1,
            status=ScheduleMonthStatus.DRAFT.value,
            is_operational_test=True,
        )
        military = Military(
            name="Operacional Quatro",
            nim="900004",
            functional_type=FunctionalType.SEC.value,
            start_date=date(2026, 1, 1),
        )
        db.session.add_all([schedule_month, version, military])
        db.session.flush()
        db.session.add(
            Assignment(
                schedule_version_id=version.id,
                military_id=military.id,
                assignment_date=date(2026, 4, 1),
                code="AT1",
                source=AssignmentSource.MANUAL.value,
                is_manual=True,
            )
        )
        db.session.commit()

        excel = ScheduleExcelExportService().export_version(schedule_month, version)
        pdf = SchedulePdfExportService().export_version(schedule_month, version)

        assert "Teste_Operacional" in excel.filename
        assert "Teste_Operacional" in pdf.filename


def test_cycle_conference_route(client, app):
    with app.app_context():
        team = db.session.get(Team, 1)
        db.session.add(
            TeamCycleReference(
                team_id=team.id,
                reference_date=date(2026, 1, 5),
                reference_phase=1,
                valid_from=date(2026, 1, 1),
            )
        )
        db.session.commit()
        url = f"/controlo-operacional/ciclo?team_id={team.id}&start_date=2026-01-05&end_date=2026-01-07"

    response = client.get(url)

    assert response.status_code == 200
    assert b"2026-01-05" in response.data
