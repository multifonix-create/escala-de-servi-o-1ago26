from datetime import date

import pytest

from app.extensions import db
from app.models import (
    Assignment,
    AssignmentSource,
    CompensatoryLeaveCredit,
    CompensatoryLeaveCreditStatus,
    FunctionalType,
    Holiday,
    Military,
    MilitaryTeamHistory,
    RescheduledRestCredit,
    RescheduledRestCreditStatus,
    ScheduleMonth,
    ScheduleMonthStatus,
    ScheduleVersion,
    ScheduleVersionSource,
    Team,
    TeamCycleReference,
    Unavailability,
    UnavailabilityStatus,
)
from app.services.assignment_service import AssignmentServiceError, clear_assignment, save_manual_assignment
from app.services.compensation_service import (
    CompensationMaintenanceService,
    CompensationServiceError,
    cancel_fc_schedule,
    cancel_fr_schedule,
    confirm_fc_from_assignment,
    confirm_fr_from_assignment,
    create_commander_discretionary_credit,
    fc_balance_by_military,
    fr_balance_by_military,
    list_compensation_potentials,
    schedule_fc_credit,
    schedule_fr_credit,
)
from app.services.diagnostic_service import ScheduleDiagnosticService
from app.services.holiday_credit_service import list_potential_credits
from app.services.schedule_regeneration import copy_preserved_assignments


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


def _draft_version(schedule_month, number=2):
    version = ScheduleVersion(
        schedule_month=schedule_month,
        version_number=number,
        status=ScheduleMonthStatus.DRAFT.value,
        source=ScheduleVersionSource.MANUAL.value,
    )
    db.session.add(version)
    db.session.commit()
    return version


def _military(functional_type=FunctionalType.SEC.value, nim="770001"):
    military = Military(
        name=f"Militar {nim}",
        nim=nim,
        functional_type=functional_type,
        start_date=date(2026, 1, 1),
    )
    db.session.add(military)
    db.session.commit()
    return military


def _patrol_military():
    team = Team.query.filter_by(code="C").one()
    military = _military(FunctionalType.PATRULHEIRO.value, "770002")
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
    return military


def _manual_assignment(version, military, assignment_date, code):
    assignment = Assignment(
        schedule_version_id=version.id,
        military_id=military.id,
        assignment_date=assignment_date,
        code=code,
        source=AssignmentSource.MANUAL.value,
        is_manual=True,
        is_locked=True,
        has_override=False,
        is_cleared=False,
    )
    db.session.add(assignment)
    db.session.commit()
    return assignment


def test_r_friday_creates_one_fc_and_saturday_creates_two(app):
    with app.app_context():
        _, version = _month()
        military = _military()
        friday = _manual_assignment(version, military, date(2026, 1, 2), "R")
        saturday = _manual_assignment(version, military, date(2026, 1, 3), "CR")

        assert len(confirm_fc_from_assignment(friday)) == 1
        assert len(confirm_fc_from_assignment(saturday)) == 2
        assert CompensatoryLeaveCredit.query.count() == 3
        assert {credit.minutes for credit in CompensatoryLeaveCredit.query.all()} == {480}


def test_r_cr_on_holiday_creates_ff_potential_but_no_fc(app):
    with app.app_context():
        _, version = _month()
        military = _military()
        assignment = _manual_assignment(version, military, date(2026, 1, 6), "R")
        db.session.add(Holiday(holiday_date=date(2026, 1, 6), name="Feriado Teste", scope="NATIONAL", is_active=True))
        db.session.commit()

        with pytest.raises(CompensationServiceError):
            confirm_fc_from_assignment(assignment)
        assert list_potential_credits(version)[0].assignment.id == assignment.id
        assert CompensatoryLeaveCredit.query.count() == 0


def test_commander_discretion_requires_positive_integer_and_reason(app):
    with app.app_context():
        military = _military()

        with pytest.raises(CompensationServiceError):
            create_commander_discretionary_credit({"military_id": str(military.id), "acquired_date": "2026-01-10", "units": "0", "commander_reason": "Autorizado"})
        with pytest.raises(CompensationServiceError):
            create_commander_discretionary_credit({"military_id": str(military.id), "acquired_date": "2026-01-10", "units": "1", "commander_reason": ""})

        credits = create_commander_discretionary_credit({"military_id": str(military.id), "acquired_date": "2026-01-10", "units": "2", "commander_reason": "Decisao documentada"})
        assert len(credits) == 2
        assert [credit.unit_number for credit in credits] == [1, 2]


def test_fr_is_created_from_at_po_pt_on_ds_dc_without_changing_cycle(app):
    with app.app_context():
        _, version = _month()
        military = _patrol_military()
        assignment, validation = save_manual_assignment(
            version,
            military,
            date(2026, 1, 5),
            "AT1",
            override_requested=True,
            override_reason="Servico em DS para testar FR",
        )
        assert validation.cycle_code == "DS"

        credit = confirm_fr_from_assignment(assignment)

        assert credit.original_rest_type == "DS"
        assert credit.source_service_code == "AT1"
        assert RescheduledRestCredit.query.count() == 1


def test_detects_pending_fc_and_fr_potentials(app):
    with app.app_context():
        _, version = _month()
        sec = _military()
        patrol = _patrol_military()
        _manual_assignment(version, sec, date(2026, 1, 2), "R")
        save_manual_assignment(
            version,
            patrol,
            date(2026, 1, 5),
            "PO1",
            override_requested=True,
            override_reason="Servico em DS",
        )

        fc_potentials, fr_potentials = list_compensation_potentials(version)

        assert len(fc_potentials) == 1
        assert fc_potentials[0].units == 1
        assert len(fr_potentials) == 1
        assert fr_potentials[0].original_rest_type == "DS"


def test_schedule_fc_creates_locked_manual_assignment_and_blocks_generic_clear(app):
    with app.app_context():
        schedule_month, version = _month()
        military = _military()
        credit = create_commander_discretionary_credit({"military_id": str(military.id), "acquired_date": "2026-01-10", "units": "1", "commander_reason": "Teste"})[0]

        assignment = schedule_fc_credit(credit, version, date(2026, 1, 12), "Agendar FC")

        assert assignment.code == "FC"
        assert assignment.is_manual is True
        assert assignment.is_locked is True
        assert assignment.compensatory_leave_credit_id == credit.id
        assert version.content_revision == 1
        with pytest.raises(AssignmentServiceError):
            clear_assignment(assignment)


def test_fc_scheduling_blocks_occupied_cell_unavailability_and_non_draft(app):
    with app.app_context():
        _, version = _month()
        military = _military()
        credit = create_commander_discretionary_credit({"military_id": str(military.id), "acquired_date": "2026-01-10", "units": "1", "commander_reason": "Teste"})[0]
        _manual_assignment(version, military, date(2026, 1, 12), "AT1")

        with pytest.raises(CompensationServiceError):
            schedule_fc_credit(credit, version, date(2026, 1, 12))

        version.status = ScheduleMonthStatus.VALIDATED.value
        db.session.commit()
        with pytest.raises(CompensationServiceError):
            schedule_fc_credit(credit, version, date(2026, 1, 13))

        version.status = ScheduleMonthStatus.DRAFT.value
        db.session.add(Unavailability(military_id=military.id, code="LF", start_date=date(2026, 1, 13), end_date=date(2026, 1, 13), is_full_day=True, status=UnavailabilityStatus.CONFIRMED.value, reason="Teste"))
        db.session.commit()
        with pytest.raises(CompensationServiceError):
            schedule_fc_credit(credit, version, date(2026, 1, 13))


def test_fc_expiry_and_protection_after_scheduling(app):
    with app.app_context():
        schedule_month, version = _month(year=2027, month=1)
        military = Military(name="Militar FC 2027", nim="770003", functional_type=FunctionalType.SEC.value, start_date=date(2026, 1, 1))
        db.session.add(military)
        db.session.commit()
        credit = create_commander_discretionary_credit({"military_id": str(military.id), "acquired_date": "2026-12-31", "units": "1", "commander_reason": "Teste"})[0]

        schedule_fc_credit(credit, version, date(2027, 1, 2))
        assert credit.expiry_protected_at is not None

        cancel_fc_schedule(credit, today=date(2027, 1, 3))
        assert credit.status == CompensatoryLeaveCreditStatus.EXPIRED.value


def test_fc_auto_used_only_with_official_version(app):
    with app.app_context():
        schedule_month, version = _month()
        military = _military()
        credit = create_commander_discretionary_credit({"military_id": str(military.id), "acquired_date": "2026-01-02", "units": "1", "commander_reason": "Teste"})[0]
        schedule_fc_credit(credit, version, date(2026, 1, 3))

        CompensationMaintenanceService().process(today=date(2026, 1, 4))
        assert credit.status == CompensatoryLeaveCreditStatus.SCHEDULED.value

        version.status = ScheduleMonthStatus.PUBLISHED.value
        schedule_month.status = ScheduleMonthStatus.PUBLISHED.value
        schedule_month.published_version_id = version.id
        db.session.commit()
        CompensationMaintenanceService().process(today=date(2026, 1, 4))
        assert credit.status == CompensatoryLeaveCreditStatus.USED.value
        assert credit.effective_date == date(2026, 1, 3)


def test_schedule_fr_cancel_and_confirm_used(app):
    with app.app_context():
        _, version = _month()
        target_version = _draft_version(version.schedule_month)
        military = _patrol_military()
        assignment, _ = save_manual_assignment(
            version,
            military,
            date(2026, 1, 5),
            "PT",
            override_requested=True,
            override_reason="Servico em DS",
        )
        credit = confirm_fr_from_assignment(assignment)

        scheduled = schedule_fr_credit(credit, target_version, date(2026, 1, 8))
        assert scheduled.code == "FR"
        assert credit.status == RescheduledRestCreditStatus.SCHEDULED.value

        cancel_fr_schedule(credit)
        assert credit.status == RescheduledRestCreditStatus.PENDING.value
        scheduled = schedule_fr_credit(credit, target_version, date(2026, 1, 9))
        assert scheduled.rescheduled_rest_credit_id == credit.id


def test_balances_keep_fc_and_fr_separate(app):
    with app.app_context():
        _, version = _month()
        military = _patrol_military()
        create_commander_discretionary_credit({"military_id": str(military.id), "acquired_date": "2026-01-10", "units": "1", "commander_reason": "Teste"})
        assignment, _ = save_manual_assignment(
            version,
            military,
            date(2026, 1, 5),
            "AT2",
            override_requested=True,
            override_reason="Servico em DS",
        )
        confirm_fr_from_assignment(assignment)

        fc_balance = next(item for item in fc_balance_by_military() if item.military.id == military.id)
        fr_balance = next(item for item in fr_balance_by_military() if item.military.id == military.id)

        assert fc_balance.available == 1
        assert fr_balance.available == 1


def test_regeneration_preserves_fc_and_fr_links(app):
    with app.app_context():
        schedule_month, source = _month()
        result = _draft_version(schedule_month)
        military = _patrol_military()
        fc = create_commander_discretionary_credit({"military_id": str(military.id), "acquired_date": "2026-01-10", "units": "1", "commander_reason": "Teste"})[0]
        fr_source, _ = save_manual_assignment(source, military, date(2026, 1, 5), "PO2", override_requested=True, override_reason="Servico em DS")
        fr = confirm_fr_from_assignment(fr_source)
        schedule_fc_credit(fc, source, date(2026, 1, 8))
        schedule_fr_credit(fr, source, date(2026, 1, 9))

        copied, skipped = copy_preserved_assignments(source, result)
        db.session.commit()

        assert copied >= 2
        assert skipped == 0
        assert Assignment.query.filter_by(schedule_version_id=result.id, code="FC", compensatory_leave_credit_id=fc.id, is_cleared=False).count() == 1
        assert Assignment.query.filter_by(schedule_version_id=result.id, code="FR", rescheduled_rest_credit_id=fr.id, is_cleared=False).count() == 1


def test_diagnostics_report_unprocessed_and_incoherent_compensations(app):
    with app.app_context():
        _, version = _month()
        military = _military()
        _manual_assignment(version, military, date(2026, 1, 2), "R")
        credit = create_commander_discretionary_credit({"military_id": str(military.id), "acquired_date": "2026-01-10", "units": "1", "commander_reason": "Teste"})[0]
        credit.status = CompensatoryLeaveCreditStatus.SCHEDULED.value
        credit.scheduled_date = date(2026, 1, 12)
        db.session.commit()

        problems, _ = ScheduleDiagnosticService().analyze(version)
        codes = {item.code for item in problems}

        assert "FC-POTENTIAL-RIGHT-UNPROCESSED" in codes
        assert "FC-SCHEDULED-WITHOUT-CELL" in codes


def test_compensation_routes_are_available(client):
    assert client.get("/fc").status_code == 200
    assert client.get("/fc/novo").status_code == 200
    assert client.get("/folgas-reagendadas").status_code == 200
