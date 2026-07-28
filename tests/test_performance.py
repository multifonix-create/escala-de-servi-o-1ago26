from contextlib import contextmanager
from datetime import date

from sqlalchemy import event

from app.extensions import db
from app.models import (
    FunctionalType,
    Military,
    MilitaryTeamHistory,
    OFFICIAL_TEAM_CODES,
    ScheduleMonth,
    ScheduleMonthStatus,
    ScheduleVersion,
    ScheduleVersionSource,
    Team,
    TeamCycleReference,
)
from app.services.diagnostic_service import ScheduleDiagnosticService
from app.services.monthly_grid_builder import build_monthly_grid
from app.services.schedule_generator import ScheduleGenerator


@contextmanager
def query_counter():
    data = {"count": 0}

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        data["count"] += 1

    event.listen(db.engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield data
    finally:
        event.remove(db.engine, "before_cursor_execute", before_cursor_execute)


def _performance_context(count=25):
    schedule_month = ScheduleMonth(year=2026, month=1, status=ScheduleMonthStatus.DRAFT.value)
    version = ScheduleVersion(
        schedule_month=schedule_month,
        version_number=1,
        status=ScheduleMonthStatus.DRAFT.value,
        source=ScheduleVersionSource.INITIAL.value,
    )
    db.session.add_all([schedule_month, version])
    db.session.flush()
    teams = Team.query.order_by(Team.code.asc()).all()
    for index, team in enumerate(teams):
        db.session.add(
            TeamCycleReference(
                team_id=team.id,
                reference_date=date(2026, 1, 5),
                reference_phase=(index % 6) + 1,
                valid_from=date(2025, 10, 1),
            )
        )
    db.session.flush()
    for index in range(count):
        military = Military(
            name=f"Militar Performance {index:03d}",
            nim=f"990{index:04d}",
            functional_type=FunctionalType.PATRULHEIRO.value,
            start_date=date(2025, 10, 1),
        )
        db.session.add(military)
        db.session.flush()
        db.session.add(
            MilitaryTeamHistory(
                military_id=military.id,
                team_id=teams[index % len(OFFICIAL_TEAM_CODES)].id,
                start_date=date(2025, 10, 1),
            )
        )
    db.session.commit()
    return schedule_month, version


def test_generation_uses_preloaded_context_without_candidate_query_explosion(app):
    with app.app_context():
        _, version = _performance_context(25)

        with query_counter() as counter:
            ScheduleGenerator().generate_at_po(version)

        assert counter["count"] < 10_000


def test_monthly_grid_uses_batch_loading_without_cell_query_explosion(app):
    with app.app_context():
        schedule_month, version = _performance_context(25)
        ScheduleGenerator().generate_at_po(version)

        with query_counter() as counter:
            build_monthly_grid(schedule_month, version)

        assert counter["count"] < 500


def test_diagnostic_uses_batch_loading_for_generated_version(app):
    with app.app_context():
        _, version = _performance_context(25)
        ScheduleGenerator().generate_at_po(version)

        with query_counter() as counter:
            ScheduleDiagnosticService().run_and_persist(version)

        assert counter["count"] < 700
