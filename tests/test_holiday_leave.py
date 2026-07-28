from datetime import date

import pytest

from app.extensions import db
from app.models import (
    Assignment,
    AssignmentChange,
    FunctionalType,
    Holiday,
    HolidayLeaveCredit,
    HolidayLeaveCreditEvent,
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
from app.services.assignment_service import AssignmentServiceError, clear_assignment, save_manual_assignment, unlock_assignment
from app.services.diagnostic_service import ScheduleDiagnosticService
from app.services.holiday_credit_service import (
    HolidayCreditServiceError,
    cancel_schedule,
    create_credit_from_assignment,
    create_holiday,
    list_potential_credits,
    schedule_credit,
)
from app.services.schedule_regeneration import ScheduleRegenerationService


def _context(status=ScheduleMonthStatus.DRAFT.value):
    team = Team.query.filter_by(code="C").one()
    military = Military(
        name="Militar FF",
        nim="880001",
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


def _holiday():
    holiday = Holiday(
        holiday_date=date(2026, 1, 6),
        name="Feriado de Teste",
        scope="NATIONAL",
        is_active=True,
    )
    db.session.add(holiday)
    db.session.commit()
    return holiday


def _draft_version(schedule_month):
    version = ScheduleVersion(
        schedule_month=schedule_month,
        version_number=2,
        status=ScheduleMonthStatus.DRAFT.value,
        source=ScheduleVersionSource.MANUAL.value,
    )
    db.session.add(version)
    db.session.commit()
    return version


def test_holiday_crud_does_not_seed_realistic_data(app):
    with app.app_context():
        holiday = create_holiday(
            {
                "holiday_date": "2026-01-06",
                "name": "Feriado de Teste",
                "scope": "NATIONAL",
                "notes": "",
            }
        )

        assert holiday.id is not None
        assert Holiday.query.count() == 1
        assert Military.query.count() == 0
        assert HolidayLeaveCredit.query.count() == 0


def test_ff_credit_is_created_from_holiday_assignment_and_keeps_service_code(app):
    with app.app_context():
        military, _, version = _context()
        holiday = _holiday()
        assignment, _ = save_manual_assignment(version, military, date(2026, 1, 6), "PO2")
        version.status = ScheduleMonthStatus.VALIDATED.value
        db.session.commit()

        credit = create_credit_from_assignment(assignment, holiday)
        again = create_credit_from_assignment(assignment, holiday)

        db.session.refresh(assignment)
        assert credit.id == again.id
        assert credit.status == "PENDING"
        assert credit.service_code == "PO2"
        assert assignment.code == "PO2"
        assert assignment.holiday_leave_credit_id is None
        assert HolidayLeaveCreditEvent.query.filter_by(event_type="CREATED").count() == 1


def test_ff_processing_route_creates_selected_credit_with_explicit_confirmation(client, app):
    with app.app_context():
        military, _, version = _context()
        _holiday()
        assignment, _ = save_manual_assignment(version, military, date(2026, 1, 6), "PO2")
        version_id = version.id
        assignment_id = assignment.id

    response = client.post(
        f"/escala/2026/1/versoes/{version_id}/ff/processar",
        data={"confirm_service_performed": "on", "assignment_id": str(assignment_id)},
        follow_redirects=True,
    )

    assert response.status_code == 200
    with app.app_context():
        assert HolidayLeaveCredit.query.count() == 1


def test_holiday_and_ff_index_routes_respond(client):
    assert client.get("/feriados").status_code == 200
    assert client.get("/feriados/novo").status_code == 200
    assert client.get("/ff").status_code == 200


def test_priority_real_case_ff_schedule_regeneration_and_cancel(app):
    with app.app_context():
        military, schedule_month, source_version = _context()
        holiday = _holiday()
        source_assignment, _ = save_manual_assignment(source_version, military, date(2026, 1, 6), "PO2")
        source_version.status = ScheduleMonthStatus.VALIDATED.value
        db.session.commit()
        credit = create_credit_from_assignment(source_assignment, holiday)
        target_version = _draft_version(schedule_month)

        ff_assignment = schedule_credit(credit, target_version, date(2026, 1, 7), notes="FF autorizada")

        assert ff_assignment.code == "FF"
        assert ff_assignment.source == "MANUAL"
        assert ff_assignment.is_manual is True
        assert ff_assignment.is_locked is True
        assert ff_assignment.holiday_leave_credit_id == credit.id
        assert source_assignment.code == "PO2"
        assert credit.status == "SCHEDULED"

        summary = ScheduleRegenerationService().regenerate_automatic_at_po(target_version)
        copied = Assignment.query.filter_by(
            schedule_version_id=summary.result_version_id,
            military_id=military.id,
            assignment_date=date(2026, 1, 7),
            code="FF",
            holiday_leave_credit_id=credit.id,
            is_cleared=False,
        ).one()

        assert copied.holiday_leave_credit_id == credit.id
        cancel_schedule(credit, "Teste de cancelamento")

        assert credit.status == "PENDING"
        assert credit.scheduled_date is None
        assert Assignment.query.filter_by(holiday_leave_credit_id=credit.id, code="FF", is_cleared=False).count() == 0
        assert AssignmentChange.query.filter_by(change_type="CLEARED").count() >= 2
        assert Assignment.query.filter(Assignment.code.in_(["FC"])).count() == 0


def test_ff_schedule_blocks_ds_dc_and_unavailability(app):
    with app.app_context():
        military, schedule_month, source_version = _context()
        holiday = _holiday()
        source_assignment, _ = save_manual_assignment(source_version, military, date(2026, 1, 6), "PO2")
        credit = create_credit_from_assignment(source_assignment, holiday, manual_confirmation=True)
        target_version = _draft_version(schedule_month)

        with pytest.raises(HolidayCreditServiceError):
            schedule_credit(credit, target_version, date(2026, 1, 5))

        db.session.add(
            Unavailability(
                military_id=military.id,
                code="LF",
                start_date=date(2026, 1, 7),
                end_date=date(2026, 1, 7),
                is_full_day=True,
                status=UnavailabilityStatus.CONFIRMED.value,
                reason="Teste",
            )
        )
        db.session.commit()

        with pytest.raises(HolidayCreditServiceError):
            schedule_credit(credit, target_version, date(2026, 1, 7))


def test_generic_clear_is_blocked_for_ff_credit_cell(app):
    with app.app_context():
        military, schedule_month, source_version = _context()
        holiday = _holiday()
        source_assignment, _ = save_manual_assignment(source_version, military, date(2026, 1, 6), "PO2")
        credit = create_credit_from_assignment(source_assignment, holiday, manual_confirmation=True)
        target_version = _draft_version(schedule_month)
        ff_assignment = schedule_credit(credit, target_version, date(2026, 1, 7))
        unlock_assignment(ff_assignment, "Tentativa generica")

        with pytest.raises(AssignmentServiceError):
            clear_assignment(ff_assignment)


def test_ff_diagnostics_detects_unprocessed_and_incoherent_cells(app):
    with app.app_context():
        military, _, version = _context()
        _holiday()
        save_manual_assignment(version, military, date(2026, 1, 6), "PO2")
        manual_ff, _ = save_manual_assignment(
            version,
            military,
            date(2026, 1, 7),
            "FF",
            override_requested=True,
            override_reason="Teste controlado de FF sem credito",
        )

        problems, _ = ScheduleDiagnosticService().analyze(version)
        codes = {item.code for item in problems}

        assert "FF-POTENTIAL-RIGHT-UNPROCESSED" in codes
        assert "FF-CELL-WITHOUT-CREDIT" in codes
        assert manual_ff.holiday_leave_credit_id is None
