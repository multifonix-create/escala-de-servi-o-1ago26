from datetime import date

import pytest

from app.extensions import db
from app.models import (
    Assignment,
    AssignmentSource,
    FunctionalType,
    Military,
    ScheduleMonth,
    ScheduleMonthStatus,
    ScheduleVersion,
    ScheduleVersionSource,
    ScheduleVersionStateEvent,
    Team,
    TeamCycleReference,
)
from app.services.assignment_service import AssignmentServiceError, save_manual_assignment
from app.services.service_code_catalog import COVERAGE_TARGETS
from app.services.schedule_version_workflow import ScheduleVersionWorkflow, ScheduleWorkflowError


def _month(year=2026, month=1):
    schedule_month = ScheduleMonth(year=year, month=month, status=ScheduleMonthStatus.DRAFT.value)
    version = ScheduleVersion(
        schedule_month=schedule_month,
        version_number=1,
        status=ScheduleMonthStatus.DRAFT.value,
        source=ScheduleVersionSource.INITIAL.value,
    )
    db.session.add_all([schedule_month, version])
    db.session.commit()
    return schedule_month, version


def _military(index):
    military = Military(
        name=f"Militar Workflow {index:03d}",
        nim=f"990{index:03d}",
        functional_type=FunctionalType.SEC.value,
        start_date=date(2026, 1, 1),
    )
    db.session.add(military)
    db.session.flush()
    return military


def _fill_mandatory_coverage(version):
    _cycle_references()
    index = 1
    for day in range(1, 32):
        assignment_date = date(2026, 1, day)
        for code, target in COVERAGE_TARGETS.items():
            for _ in range(target):
                military = _military(index)
                index += 1
                db.session.add(
                    Assignment(
                        schedule_version_id=version.id,
                        military_id=military.id,
                        assignment_date=assignment_date,
                        code=code,
                        source=AssignmentSource.SYSTEM.value,
                        is_manual=False,
                        is_locked=False,
                        has_override=False,
                        is_cleared=False,
                    )
                )
    version.content_revision = 1
    db.session.commit()


def _cycle_references():
    for team in Team.query.order_by(Team.code.asc()).all():
        db.session.add(
            TeamCycleReference(
                team_id=team.id,
                reference_date=date(2026, 1, 5),
                reference_phase=6,
                valid_from=date(2026, 1, 1),
            )
        )
    db.session.flush()


def _support_militaries(count=9):
    for index in range(1, count + 1):
        military = Military(
            name=f"Militar Workflow {index:02d}",
            nim=f"990{index:03d}",
            functional_type=FunctionalType.SEC.value,
            start_date=date(2026, 1, 1),
        )
        db.session.add(military)
    db.session.commit()


def _generated_validated_version():
    schedule_month, version = _month()
    _fill_mandatory_coverage(version)
    ScheduleVersionWorkflow().validate_version(version, confirm_warnings=True)
    db.session.refresh(version)
    return schedule_month, version


def test_validation_runs_diagnostic_and_blocks_incomplete_coverage(app):
    with app.app_context():
        _, version = _month()

        with pytest.raises(ScheduleWorkflowError) as exc_info:
            ScheduleVersionWorkflow().validate_version(version)

        assert exc_info.value.diagnostic_run is not None
        assert any(issue.code == "COVERAGE-MISSING" for issue in exc_info.value.blockers)
        assert version.status == ScheduleMonthStatus.DRAFT.value


def test_validation_stores_revision_and_state_event(app):
    with app.app_context():
        _, version = _generated_validated_version()

        assert version.status == ScheduleMonthStatus.VALIDATED.value
        assert version.validated_revision == version.content_revision
        assert version.validated_diagnostic_run_id is not None
        assert ScheduleVersionStateEvent.query.filter_by(event_type="VALIDATED").count() == 1


def test_publish_replaces_previous_published_version(app):
    with app.app_context():
        schedule_month, first = _generated_validated_version()
        workflow = ScheduleVersionWorkflow()
        workflow.publish_version(first)

        second = ScheduleVersion(
            schedule_month=schedule_month,
            version_number=2,
            status=ScheduleMonthStatus.DRAFT.value,
            source=ScheduleVersionSource.MANUAL.value,
        )
        db.session.add(second)
        db.session.commit()
        for assignment in first.assignments:
            db.session.add(
                Assignment(
                    schedule_version_id=second.id,
                    military_id=assignment.military_id,
                    assignment_date=assignment.assignment_date,
                    code=assignment.code,
                    source=assignment.source,
                    is_manual=assignment.is_manual,
                    is_locked=assignment.is_locked,
                    has_override=assignment.has_override,
                    is_cleared=False,
                )
            )
        second.content_revision = 1
        db.session.commit()
        workflow.validate_version(second, confirm_warnings=True)
        workflow.publish_version(second, confirm_replace=True)

        db.session.refresh(first)
        db.session.refresh(second)
        db.session.refresh(schedule_month)
        assert first.status == ScheduleMonthStatus.VALIDATED.value
        assert second.status == ScheduleMonthStatus.PUBLISHED.value
        assert schedule_month.published_version_id == second.id
        assert ScheduleVersion.query.filter_by(schedule_month_id=schedule_month.id, status=ScheduleMonthStatus.PUBLISHED.value).count() == 1


def test_publish_blocks_when_content_changed_after_validation(app):
    with app.app_context():
        _, version = _generated_validated_version()
        version.content_revision += 1
        db.session.commit()

        with pytest.raises(ScheduleWorkflowError):
            ScheduleVersionWorkflow().publish_version(version)


def test_close_makes_version_immutable_and_correction_copies_visible_assignments(app):
    with app.app_context():
        _, version = _generated_validated_version()
        workflow = ScheduleVersionWorkflow()
        workflow.publish_version(version)
        workflow.close_version(version, today=date(2026, 2, 1))

        assignment = Assignment.query.filter_by(schedule_version_id=version.id, is_cleared=False).first()
        with pytest.raises(AssignmentServiceError):
            save_manual_assignment(version, assignment.military, assignment.assignment_date, "AT1")

        correction = workflow.create_correction_version(version, "Correcao operacional.")

        assert version.status == ScheduleMonthStatus.CLOSED.value
        assert correction.status == ScheduleMonthStatus.DRAFT.value
        assert correction.parent_version_id == version.id
        assert Assignment.query.filter_by(schedule_version_id=correction.id, is_cleared=False).count() == Assignment.query.filter_by(schedule_version_id=version.id, is_cleared=False).count()
        assert ScheduleVersionStateEvent.query.filter_by(event_type="REOPENED_AS_NEW_VERSION").count() == 1


def test_workflow_routes_are_available(client, app):
    with app.app_context():
        schedule_month, version = _month()
        year = schedule_month.year
        month = schedule_month.month
        version_id = version.id

    assert client.get(f"/escala/{year}/{month}/versoes/{version_id}/validar").status_code == 200
    assert client.get(f"/escala/{year}/{month}/versoes/{version_id}/historico-estado").status_code == 200
