from datetime import date, time

import pytest

from app.extensions import db
from app.models import (
    Assignment,
    AssignmentSelectionDetail,
    FunctionalType,
    GenerationMode,
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
from app.services.schedule_generator import PTGenerationOptions, ScheduleGenerationError, ScheduleGenerator
from app.services.schedule_regeneration import ScheduleRegenerationService


def _month(year=2026, month=1, status=ScheduleMonthStatus.DRAFT.value):
    schedule_month = ScheduleMonth(year=year, month=month, status=status)
    version = ScheduleVersion(
        schedule_month=schedule_month,
        version_number=1,
        status=status,
        source=ScheduleVersionSource.INITIAL.value,
    )
    db.session.add_all([schedule_month, version])
    db.session.commit()
    return schedule_month, version


def _reference(team_code="A", reference_date=date(2026, 1, 5), reference_phase=6):
    team = Team.query.filter_by(code=team_code).one()
    db.session.add(
        TeamCycleReference(
            team_id=team.id,
            reference_date=reference_date,
            reference_phase=reference_phase,
            valid_from=date(2026, 1, 1),
        )
    )
    db.session.commit()
    return team


def _military(index, functional_type=FunctionalType.PATRULHEIRO.value, team=None):
    military = Military(
        name=f"Militar PT {index:02d}",
        nim=f"920{index:03d}",
        functional_type=functional_type,
        start_date=date(2026, 1, 1),
    )
    db.session.add(military)
    db.session.flush()
    if team is not None:
        db.session.add(
            MilitaryTeamHistory(
                military_id=military.id,
                team_id=team.id,
                start_date=date(2026, 1, 1),
            )
        )
    db.session.commit()
    return military


def _patrols(count, team_code="A", start_index=1):
    team = _reference(team_code)
    return [_military(index, team=team) for index in range(start_index, start_index + count)]


def _pt_options(**kwargs):
    values = {
        "enabled": True,
        "duration_hours": 8,
        "start_time": time(8, 0),
        "max_daily": 1,
    }
    values.update(kwargs)
    return PTGenerationOptions(**values)


def _count(version, assignment_date, code):
    return Assignment.query.filter_by(
        schedule_version_id=version.id,
        assignment_date=assignment_date,
        code=code,
        is_cleared=False,
    ).count()


def test_pt_is_disabled_by_default(app):
    with app.app_context():
        _, version = _month()
        _patrols(12)

        ScheduleGenerator().generate_at_po(version)

        assert Assignment.query.filter_by(code="PT").count() == 0


def test_pt_requires_valid_duration_and_start_time(app):
    with app.app_context():
        _, version = _month()
        _patrols(12)

        with pytest.raises(ScheduleGenerationError):
            ScheduleGenerator().generate_at_po(version, PTGenerationOptions(enabled=True, duration_hours=7, start_time=None, max_daily=1))


def test_pt_is_created_only_after_complete_at_po_coverage(app):
    with app.app_context():
        _, version = _month()
        _patrols(12)

        run = ScheduleGenerator().generate_at_po(version, _pt_options(max_daily=2))

        assert _count(version, date(2026, 1, 1), "AT1") == 1
        assert _count(version, date(2026, 1, 1), "PO1") == 2
        assert _count(version, date(2026, 1, 1), "PT") == 2
        pt = Assignment.query.filter_by(code="PT", assignment_date=date(2026, 1, 1)).first()
        assert pt.source == "SYSTEM"
        assert pt.is_manual is False
        assert pt.is_locked is False
        assert pt.start_time == time(8, 0)
        assert pt.end_time == time(16, 0)
        assert pt.duration_minutes == 480
        assert '"pt_created"' in run.summary_json


def test_pt_is_blocked_when_at_po_coverage_is_incomplete(app):
    with app.app_context():
        _, version = _month()
        _patrols(8)

        ScheduleGenerator().generate_at_po(version, _pt_options())

        assert Assignment.query.filter_by(code="PT").count() == 0
        assert AssignmentSelectionDetail.query.filter(
            AssignmentSelectionDetail.service_code == "PT",
            AssignmentSelectionDetail.reason.contains("cobertura AT/PO incompleta"),
        ).count() > 0


def test_manual_pt_counts_for_daily_limit_and_is_preserved(app):
    with app.app_context():
        _, version = _month()
        patrols = _patrols(12)
        manual = Assignment(
            schedule_version_id=version.id,
            military_id=patrols[-1].id,
            assignment_date=date(2026, 1, 1),
            code="PT",
            source="MANUAL",
            is_manual=True,
            is_locked=True,
            start_time=time(8, 0),
            end_time=time(16, 0),
            duration_minutes=480,
        )
        db.session.add(manual)
        db.session.commit()

        ScheduleGenerator().generate_at_po(version, _pt_options(max_daily=2))

        db.session.refresh(manual)
        assert manual.source == "MANUAL"
        assert _count(version, date(2026, 1, 1), "PT") == 2
        assert Assignment.query.filter_by(code="PT", source="SYSTEM", assignment_date=date(2026, 1, 1)).count() == 1


def test_pt_excludes_ds_dc_cmd_unavailability_restriction_and_rest(app):
    with app.app_context():
        _, version = _month()
        main_team = _reference("A")
        rest_team = _reference("B", reference_date=date(2026, 1, 1), reference_phase=3)
        main = [_military(index, team=main_team) for index in range(1, 10)]
        manual_pt = _military(20, team=main_team)
        eligible = _military(21, team=main_team)
        ds_military = _military(22, team=rest_team)
        unavailable = _military(23, team=main_team)
        restricted = _military(24, team=main_team)
        short_rest = _military(25, team=main_team)
        cmd = _military(26, FunctionalType.CMD.value)
        db.session.add(
            Assignment(
                schedule_version_id=version.id,
                military_id=manual_pt.id,
                assignment_date=date(2026, 1, 1),
                code="PT",
                source="MANUAL",
                is_manual=True,
                is_locked=True,
                start_time=time(7, 0),
                end_time=time(15, 0),
                duration_minutes=480,
            )
        )
        db.session.add(
            Assignment(
                schedule_version_id=version.id,
                military_id=short_rest.id,
                assignment_date=date(2025, 12, 31),
                code="AT3",
                source="MANUAL",
                is_manual=True,
                is_locked=True,
            )
        )
        db.session.add(
            Unavailability(
                military_id=unavailable.id,
                code="BM",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 1),
                is_full_day=True,
                status=UnavailabilityStatus.CONFIRMED.value,
                reason="Teste",
            )
        )
        db.session.add(
            MilitaryRestriction(
                military_id=restricted.id,
                restriction_type="UNAVAILABLE",
                start_date=date(2026, 1, 1),
                thursday=True,
                reason="Teste",
            )
        )
        db.session.commit()

        ScheduleGenerator().generate_at_po(version, _pt_options(start_time=time(7, 0), max_daily=2))

        pt_assignments = Assignment.query.filter_by(code="PT", assignment_date=date(2026, 1, 1)).all()
        system_pt_ids = {item.military_id for item in pt_assignments if item.source == "SYSTEM"}
        assert system_pt_ids == {eligible.id}
        assert manual_pt.id in {item.military_id for item in pt_assignments}
        assert ds_military.id not in system_pt_ids
        assert unavailable.id not in system_pt_ids
        assert restricted.id not in system_pt_ids
        assert short_rest.id not in system_pt_ids
        assert cmd.id not in system_pt_ids
        assert all(item.military_id in {military.id for military in main} for item in Assignment.query.filter(Assignment.code.in_(["AT1", "AT2", "AT3", "PO1", "PO2", "PO3"]), Assignment.assignment_date == date(2026, 1, 1)).all())


def test_regeneration_recalculates_automatic_pt_and_preserves_manual_pt(app):
    with app.app_context():
        _, version = _month()
        patrols = _patrols(12)
        db.session.add(
            Assignment(
                schedule_version_id=version.id,
                military_id=patrols[-1].id,
                assignment_date=date(2026, 1, 1),
                code="PT",
                source="MANUAL",
                is_manual=True,
                is_locked=True,
                start_time=time(8, 0),
                end_time=time(16, 0),
                duration_minutes=480,
            )
        )
        db.session.commit()
        ScheduleGenerator().generate_at_po(version, _pt_options(max_daily=2))

        summary = ScheduleRegenerationService().regenerate_automatic_at_po(version, _pt_options(duration_hours=6, start_time=time(9, 0), max_daily=2))
        result_version = db.session.get(ScheduleVersion, summary.result_version_id)
        result_pt = Assignment.query.filter_by(schedule_version_id=result_version.id, code="PT").all()

        assert Assignment.query.filter_by(schedule_version_id=result_version.id, code="PT", source="MANUAL").count() == 1
        assert Assignment.query.filter_by(schedule_version_id=result_version.id, code="PT", source="SYSTEM").count() > 0
        assert all(item.duration_minutes in {360, 480} for item in result_pt)
        assert GenerationMode.REGENERATE_AUTOMATIC.value == result_version.generation_mode


def test_generation_route_accepts_pt_parameters(client, app):
    with app.app_context():
        _, version = _month()
        _patrols(12)
        version_id = version.id

    response = client.post(
        f"/escala/2026/1/versoes/{version_id}/gerar",
        data={
            "generate_pt": "on",
            "pt_duration_hours": "6",
            "pt_start_time": "09:00",
            "pt_max_daily": "1",
            "pt_weekdays": ["0", "1", "2", "3", "4", "5", "6"],
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"PT" in response.data
