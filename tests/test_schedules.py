from datetime import date

from sqlalchemy import inspect

from app.extensions import db
from app.models import (
    CompensationStatus,
    FunctionalType,
    Military,
    MilitaryRestriction,
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
from app.services.monthly_grid_builder import build_monthly_grid
from app.services.schedule_service import create_schedule_month, get_schedule_month
from app.validators.schedule_validator import validate_schedule_month_payload


def test_schedule_month_validator_rejects_invalid_month():
    result = validate_schedule_month_payload({"year": "2026", "month": "13"})

    assert not result.is_valid
    assert "month" in result.errors


def test_create_schedule_month_creates_initial_version(app):
    with app.app_context():
        schedule_month = create_schedule_month(2026, 7)

        assert schedule_month.status == ScheduleMonthStatus.DRAFT.value
        assert schedule_month.year == 2026
        assert schedule_month.month == 7
        assert len(schedule_month.versions) == 1
        assert schedule_month.versions[0].version_number == 1
        assert schedule_month.versions[0].source == ScheduleVersionSource.INITIAL.value


def test_schedule_month_is_unique(app):
    with app.app_context():
        create_schedule_month(2026, 7)

        assert get_schedule_month(2026, 7) is not None


def test_schedule_grid_uses_dynamic_cycle_unavailabilities_and_restrictions(app):
    with app.app_context():
        team = Team.query.filter_by(code="A").one()
        military = Military(
            name="Militar Operacional",
            nim="100001",
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
        db.session.add(
            TeamCycleReference(
                team_id=team.id,
                reference_date=date(2026, 1, 5),
                reference_phase=6,
                valid_from=date(2026, 1, 1),
            )
        )
        db.session.add(
            Unavailability(
                military_id=military.id,
                code="LF",
                start_date=date(2026, 1, 5),
                end_date=date(2026, 1, 5),
                is_full_day=True,
                status=UnavailabilityStatus.CONFIRMED.value,
                reason="Teste",
                compensation_status=CompensationStatus.PENDING_DECISION.value,
            )
        )
        db.session.add(
            MilitaryRestriction(
                military_id=military.id,
                restriction_type="UNAVAILABLE",
                start_date=date(2026, 1, 5),
                monday=True,
                reason="Teste",
            )
        )
        db.session.commit()

        grid = build_monthly_grid(schedule_month)
        row = grid.rows[0]
        jan_5 = row.cells[4]
        jan_18 = row.cells[17]

        assert jan_5.cycle_code == "DS"
        assert jan_5.primary_code == "LF"
        assert jan_5.unavailability.code == "LF"
        assert jan_5.restriction_count == 1
        assert "Compensacao pendente" in grid.legend
        assert jan_18.cycle_code == "DC"


def test_schedule_grid_does_not_create_assignments_table(app):
    with app.app_context():
        tables = inspect(db.engine).get_table_names()

        assert "assignments" not in tables
        assert "schedule_assignments" not in tables


def test_schedule_index_route_responds(client):
    response = client.get("/escala")

    assert response.status_code == 200
    assert "Escala mensal".encode() in response.data


def test_empty_month_page_allows_controlled_creation(client):
    response = client.get("/escala/2026/7")

    assert response.status_code == 200
    assert "Mes ainda nao criado".encode() in response.data
    assert b"Criar mes" in response.data


def test_create_month_route_creates_draft_month(client, app):
    response = client.post("/escala/2026/7/criar", follow_redirects=True)

    assert response.status_code == 200
    assert b"DRAFT" in response.data

    with app.app_context():
        schedule_month = get_schedule_month(2026, 7)
        assert schedule_month is not None
        assert len(schedule_month.versions) == 1


def test_schedule_routes_do_not_expose_generation_controls(client):
    client.post("/escala/2026/7/criar")
    response = client.get("/escala/2026/7")

    assert response.status_code == 200
    assert b"AT1" not in response.data
    assert b"PO1" not in response.data
    assert b"PT" not in response.data
    assert b"Gerar escala" not in response.data
