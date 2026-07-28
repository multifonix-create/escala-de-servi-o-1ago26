from datetime import date

import pytest

from app.extensions import db
from app.models import (
    Assignment,
    AssignmentChange,
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
from app.services.assignment_service import (
    AssignmentServiceError,
    clear_assignment,
    save_manual_assignment,
    unlock_assignment,
    validate_assignment,
)
from app.services.monthly_grid_builder import build_monthly_grid


def _schedule_context(status=ScheduleMonthStatus.DRAFT.value):
    team = Team.query.filter_by(code="C").one()
    military = Military(
        name="Militar Teste",
        nim="200001",
        functional_type=FunctionalType.PATRULHEIRO.value,
        start_date=date(2026, 1, 1),
    )
    schedule_month = ScheduleMonth(year=2026, month=1, status=status)
    version = ScheduleVersion(
        schedule_month=schedule_month,
        version_number=1,
        status=status,
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
    db.session.add(
        TeamCycleReference(
            team_id=team.id,
            reference_date=date(2026, 1, 5),
            reference_phase=6,
            valid_from=date(2026, 1, 1),
        )
    )
    db.session.commit()
    return military, schedule_month, version


def test_manual_assignment_creates_locked_history(app):
    with app.app_context():
        military, _, version = _schedule_context()

        assignment, validation = save_manual_assignment(
            version,
            military,
            date(2026, 1, 6),
            "PO2",
            notes="Nota com acentos",
        )

        assert validation.is_valid
        assert assignment.code == "PO2"
        assert assignment.source == "MANUAL"
        assert assignment.is_manual is True
        assert assignment.is_locked is True
        assert AssignmentChange.query.filter_by(assignment_id=assignment.id, change_type="CREATED").count() == 1


def test_manual_assignment_unique_cell(app):
    with app.app_context():
        military, _, version = _schedule_context()
        save_manual_assignment(version, military, date(2026, 1, 6), "PO2")
        assignment = Assignment.query.one()

        assert assignment.schedule_version_id == version.id
        assert assignment.military_id == military.id
        assert assignment.assignment_date == date(2026, 1, 6)


def test_invalid_code_blocks_assignment(app):
    with app.app_context():
        military, _, version = _schedule_context()

        with pytest.raises(AssignmentServiceError):
            save_manual_assignment(version, military, date(2026, 1, 6), "XYZ")


def test_date_outside_month_blocks_assignment(app):
    with app.app_context():
        military, _, version = _schedule_context()

        with pytest.raises(AssignmentServiceError):
            save_manual_assignment(version, military, date(2026, 2, 1), "PO2")


def test_non_draft_version_blocks_assignment(app):
    with app.app_context():
        military, _, version = _schedule_context(status=ScheduleMonthStatus.PUBLISHED.value)

        with pytest.raises(AssignmentServiceError):
            save_manual_assignment(version, military, date(2026, 1, 6), "PO2")


def test_assignment_on_ds_requires_override(app):
    with app.app_context():
        military, _, version = _schedule_context()

        result = validate_assignment(version, military, date(2026, 1, 5), "PO2")

        assert result.requires_override is True
        assert "override" in result.blocking_errors
        assert result.cycle_code == "DS"


def test_confirmed_unavailability_requires_explicit_override(app):
    with app.app_context():
        military, _, version = _schedule_context()
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

        with pytest.raises(AssignmentServiceError):
            save_manual_assignment(version, military, date(2026, 1, 6), "PO2")

        assignment, validation = save_manual_assignment(
            version,
            military,
            date(2026, 1, 6),
            "PO2",
            override_requested=True,
            override_reason="Decisao operacional expressa",
        )

        assert assignment.has_override is True
        assert validation.requires_override is True
        assert AssignmentChange.query.filter_by(change_type="OVERRIDE_APPLIED").count() == 1


def test_bm_confirmed_blocks_normal_override(app):
    with app.app_context():
        military, _, version = _schedule_context()
        db.session.add(
            Unavailability(
                military_id=military.id,
                code="BM",
                start_date=date(2026, 1, 6),
                end_date=date(2026, 1, 6),
                is_full_day=True,
                status=UnavailabilityStatus.CONFIRMED.value,
                reason="Teste",
            )
        )
        db.session.commit()

        with pytest.raises(AssignmentServiceError):
            save_manual_assignment(
                version,
                military,
                date(2026, 1, 6),
                "PO2",
                override_requested=True,
                override_reason="Tentativa",
            )


def test_clear_preserves_history_and_dynamic_grid(app):
    with app.app_context():
        military, schedule_month, version = _schedule_context()
        assignment, _ = save_manual_assignment(version, military, date(2026, 1, 5), "DS")
        unlock_assignment(assignment, "Confirmado")
        clear_assignment(assignment, "Limpeza confirmada")

        grid = build_monthly_grid(schedule_month, version=version)
        cell = grid.rows[0].cells[4]

        assert assignment.is_cleared is True
        assert cell.primary_code == "DS"
        assert cell.manual_code is None
        assert AssignmentChange.query.filter_by(change_type="CLEARED").count() == 1


def test_grid_manual_code_prevales_and_preserves_cycle(app):
    with app.app_context():
        military, schedule_month, version = _schedule_context()
        save_manual_assignment(
            version,
            military,
            date(2026, 1, 5),
            "PO2",
            override_requested=True,
            override_reason="Servico em DS autorizado",
        )

        grid = build_monthly_grid(schedule_month, version=version)
        cell = grid.rows[0].cells[4]

        assert cell.primary_code == "PO2"
        assert cell.manual_code == "PO2"
        assert cell.cycle_code == "DS"
        assert cell.is_locked is True
        assert cell.has_override is True


def test_assignment_routes_save_and_show_history(client, app):
    with app.app_context():
        military, _, version = _schedule_context()
        version_id = version.id
        military_id = military.id

    response = client.post(
        f"/escala/2026/1/versoes/{version_id}/militares/{military_id}/dias/2026-01-06",
        data={"code": "PO2", "is_locked": "on", "notes": "Manual"},
        follow_redirects=True,
    )
    history = client.get(
        f"/escala/2026/1/versoes/{version_id}/militares/{military_id}/dias/2026-01-06/historico"
    )

    assert response.status_code == 200
    assert history.status_code == 200
    assert b"CREATED" in history.data


def test_priority_real_case_manual_po2_on_ds_with_confirmed_unavailability(app):
    with app.app_context():
        military, schedule_month, version = _schedule_context()
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

        assignment, validation = save_manual_assignment(
            version,
            military,
            date(2026, 1, 5),
            "PO2",
            override_requested=True,
            override_reason="Decisao expressa para caso real prioritario",
        )
        grid = build_monthly_grid(schedule_month, version=version)
        cell = grid.rows[0].cells[4]

        assert validation.cycle_code == "DS"
        assert validation.requires_override is True
        assert assignment.code == "PO2"
        assert assignment.is_manual is True
        assert assignment.is_locked is True
        assert assignment.has_override is True
        assert cell.primary_code == "PO2"
        assert cell.cycle_code == "DS"
        assert cell.unavailability.code == "LF"
        assert cell.has_override is True
        assert AssignmentChange.query.filter_by(change_type="CREATED").count() == 1
        assert AssignmentChange.query.filter_by(change_type="OVERRIDE_APPLIED").count() == 1
