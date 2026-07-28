from datetime import date, timedelta

from app.extensions import db
from app.models import (
    AssignmentChange,
    DiagnosticIssue,
    DiagnosticRun,
    FunctionalType,
    Military,
    MilitaryTeamHistory,
    ScheduleMonth,
    ScheduleMonthStatus,
    ScheduleVersion,
    ScheduleVersionSource,
    Team,
    TeamCycleReference,
    Unavailability,
    UnavailabilityStatus,
)
from app.services.assignment_service import save_manual_assignment
from app.services.diagnostic_service import ScheduleDiagnosticService, latest_run


def _context(with_reference=True):
    team = Team.query.filter_by(code="C").one()
    military = Military(
        name="Militar Diagnostico",
        nim="300001",
        functional_type=FunctionalType.PATRULHEIRO.value,
        start_date=date(2026, 1, 1),
    )
    schedule_month = ScheduleMonth(year=2026, month=1)
    version = ScheduleVersion(
        schedule_month=schedule_month,
        version_number=1,
        status=ScheduleMonthStatus.DRAFT.value,
        source=ScheduleVersionSource.INITIAL.value,
    )
    db.session.add_all([military, schedule_month, version])
    db.session.flush()
    db.session.add(
        MilitaryTeamHistory(
            military_id=military.id,
            team_id=team.id,
            start_date=date(2026, 1, 1),
        )
    )
    if with_reference:
        db.session.add(
            TeamCycleReference(
                team_id=team.id,
                reference_date=date(2026, 1, 5),
                reference_phase=6,
                valid_from=date(2026, 1, 1),
            )
        )
    db.session.commit()
    return military, team, schedule_month, version


def test_diagnostic_empty_execution_returns_infos(app):
    with app.app_context():
        _, _, _, version = _context()

        problems, summary = ScheduleDiagnosticService().analyze(version)

        assert summary.total_infos >= 1
        assert any(item.code == "SYSTEM-MONTH-WITHOUT-ASSIGNMENTS" for item in problems)


def test_diagnostic_persists_run_and_issues(app):
    with app.app_context():
        _, _, _, version = _context()

        run = ScheduleDiagnosticService().run_and_persist(version)

        assert run.status == "COMPLETED"
        assert DiagnosticRun.query.count() == 1
        assert DiagnosticIssue.query.count() == run.total_errors + run.total_warnings + run.total_infos
        assert latest_run(version.id).id == run.id


def test_diagnostic_detects_missing_cycle_reference(app):
    with app.app_context():
        _, _, _, version = _context(with_reference=False)

        problems, summary = ScheduleDiagnosticService().analyze(version)

        assert summary.total_errors >= 1
        assert any(item.code == "CONFIG-MISSING-CYCLE-REFERENCE" for item in problems)


def test_diagnostic_detects_service_on_ds_and_override(app):
    with app.app_context():
        military, _, _, version = _context()
        save_manual_assignment(
            version,
            military,
            date(2026, 1, 5),
            "PO2",
            override_requested=True,
            override_reason="Autorizado",
        )

        problems, _ = ScheduleDiagnosticService().analyze(version)
        codes = {item.code for item in problems}

        assert "CYCLE-MANUAL-REST-DAY" in codes
        assert "ASSIGNMENT-OVERRIDE" in codes
        assert "ASSIGNMENT-LOCKED" in codes


def test_diagnostic_detects_confirmed_unavailability_conflict(app):
    with app.app_context():
        military, _, _, version = _context()
        db.session.add(
            Unavailability(
                military_id=military.id,
                code="LF",
                start_date=date(2026, 1, 6),
                end_date=date(2026, 1, 6),
                is_full_day=True,
                status=UnavailabilityStatus.CONFIRMED.value,
                reason="Teste",
            )
        )
        db.session.commit()
        save_manual_assignment(
            version,
            military,
            date(2026, 1, 6),
            "PO2",
            override_requested=True,
            override_reason="Autorizado",
        )

        problems, _ = ScheduleDiagnosticService().analyze(version)

        assert any(item.code == "UNAV-CONFIRMED-CONFLICT" for item in problems)


def test_diagnostic_detects_short_rest_between_known_manual_services(app):
    with app.app_context():
        military, _, _, version = _context()
        save_manual_assignment(version, military, date(2026, 1, 6), "AT3")
        first = version.assignments[0]
        first.is_locked = False
        db.session.commit()
        save_manual_assignment(version, military, date(2026, 1, 7), "AT1")

        problems, _ = ScheduleDiagnosticService().analyze(version)

        assert any(item.code == "REST-TOO-SHORT" for item in problems)


def test_diagnostic_routes_execute_and_show_detail(client, app):
    with app.app_context():
        _, _, _, version = _context()
        version_id = version.id

    response = client.post(f"/escala/2026/1/versoes/{version_id}/diagnostico/executar", follow_redirects=True)

    assert response.status_code == 200
    assert b"Diagnostico" in response.data


def test_priority_real_case_diagnostic_reports_required_findings(app):
    with app.app_context():
        military, _, _, version = _context()
        db.session.add(
            Unavailability(
                military_id=military.id,
                code="LF",
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 5),
                is_full_day=True,
                status=UnavailabilityStatus.CONFIRMED.value,
                reason="Teste",
            )
        )
        db.session.commit()
        assignment, _ = save_manual_assignment(
            version,
            military,
            date(2026, 1, 5),
            "PO2",
            override_requested=True,
            override_reason="Decisao expressa",
        )

        run = ScheduleDiagnosticService().run_and_persist(version)
        codes = {issue.code for issue in run.issues}

        assert "CYCLE-MANUAL-REST-DAY" in codes
        assert "UNAV-CONFIRMED-CONFLICT" in codes
        assert "ASSIGNMENT-OVERRIDE" in codes
        assert "ASSIGNMENT-LOCKED" in codes
        assert assignment.is_locked is True
        assert AssignmentChange.query.count() >= 2
        assert not any(issue.code in {"ASSIGNMENT-COMPENSATION-CODE"} for issue in run.issues)
