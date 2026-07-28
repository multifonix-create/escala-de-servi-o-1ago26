from datetime import date

import pytest

from app.extensions import db
from app.models import (
    Assignment,
    AssignmentChange,
    AssignmentSelectionDetail,
    FunctionalType,
    GenerationRun,
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
from app.services.assignment_service import save_manual_assignment
from app.services.schedule_generator import (
    CandidateSelector,
    ScheduleGenerationError,
    ScheduleGenerator,
    build_generation_context,
    latest_generation_run,
)


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


def _reference(team_code="A"):
    team = Team.query.filter_by(code=team_code).one()
    db.session.add(
        TeamCycleReference(
            team_id=team.id,
            reference_date=date(2026, 1, 5),
            reference_phase=6,
            valid_from=date(2026, 1, 1),
        )
    )
    db.session.commit()
    return team


def _military(index, functional_type=FunctionalType.PATRULHEIRO.value, team=None):
    military = Military(
        name=f"Militar Geracao {index:02d}",
        nim=f"910{index:03d}",
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


def _patrols(count, team_code="A"):
    team = _reference(team_code)
    return [_military(index, team=team) for index in range(1, count + 1)]


def _count(version, assignment_date, code):
    return Assignment.query.filter_by(
        schedule_version_id=version.id,
        assignment_date=assignment_date,
        code=code,
        is_cleared=False,
    ).count()


def test_generation_creates_first_day_at_po_minimums(app):
    with app.app_context():
        _, version = _month()
        _patrols(9)

        run = ScheduleGenerator().generate_at_po(version)

        assert run.status in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
        assert _count(version, date(2026, 1, 1), "AT1") == 1
        assert _count(version, date(2026, 1, 1), "AT2") == 1
        assert _count(version, date(2026, 1, 1), "AT3") == 1
        assert _count(version, date(2026, 1, 1), "PO1") == 2
        assert _count(version, date(2026, 1, 1), "PO2") == 2
        assert _count(version, date(2026, 1, 1), "PO3") == 2
        assert Assignment.query.filter(Assignment.code.in_(["PT", "FF", "FC"])).count() == 0
        assert AssignmentChange.query.filter_by(change_type="CREATED").count() == Assignment.query.count()


def test_generation_preserves_manual_and_completes_only_missing(app):
    with app.app_context():
        _, version = _month()
        patrols = _patrols(9)
        manual, _ = save_manual_assignment(version, patrols[0], date(2026, 1, 1), "PO2")

        run = ScheduleGenerator().generate_at_po(version)

        db.session.refresh(manual)
        assert manual.is_manual is True
        assert manual.is_locked is True
        assert manual.code == "PO2"
        assert _count(version, date(2026, 1, 1), "PO2") == 2
        assert run.total_preserved_manual >= 1


def test_generation_does_not_use_cmd_for_at_po(app):
    with app.app_context():
        _, version = _month()
        _military(1, FunctionalType.CMD.value)

        run = ScheduleGenerator().generate_at_po(version)

        assert Assignment.query.filter_by(assignment_date=date(2026, 1, 1)).count() == 0
        assert run.total_unfilled > 0
        assert AssignmentSelectionDetail.query.filter(AssignmentSelectionDetail.reason.contains("CMD")).count() > 0


def test_generation_uses_patrol_before_sec_when_patrol_is_sufficient(app):
    with app.app_context():
        _, version = _month()
        team = _reference()
        patrol = _military(1, team=team)
        _military(2, FunctionalType.SEC.value)
        context = build_generation_context(version)

        result = CandidateSelector().select(context, date(2026, 1, 1), "AT1", 1, 0)

        assert result.selected[0].military_id == patrol.id if hasattr(result.selected[0], "military_id") else result.selected[0].military.id == patrol.id
        assert result.selected[0].military.functional_type == FunctionalType.PATRULHEIRO.value


def test_generation_uses_sec_or_si_when_patrols_are_insufficient(app):
    with app.app_context():
        _, version = _month()
        _military(1, FunctionalType.SEC.value)

        run = ScheduleGenerator().generate_at_po(version)

        selected = AssignmentSelectionDetail.query.filter_by(is_selected=True).first()
        assert selected is not None
        assert selected.military.functional_type == FunctionalType.SEC.value
        assert run.total_warnings > 0


def test_generation_excludes_confirmed_and_planned_unavailability(app):
    with app.app_context():
        _, version = _month()
        team = _reference()
        confirmed = _military(1, team=team)
        planned = _military(2, team=team)
        db.session.add_all(
            [
                Unavailability(
                    military_id=confirmed.id,
                    code="BM",
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 1, 1),
                    is_full_day=True,
                    status=UnavailabilityStatus.CONFIRMED.value,
                    reason="Teste",
                ),
                Unavailability(
                    military_id=planned.id,
                    code="LF",
                    start_date=date(2026, 1, 1),
                    end_date=date(2026, 1, 1),
                    is_full_day=True,
                    status=UnavailabilityStatus.PLANNED.value,
                    reason="Teste",
                ),
            ]
        )
        db.session.commit()

        ScheduleGenerator().generate_at_po(version)

        assert Assignment.query.filter_by(assignment_date=date(2026, 1, 1)).count() == 0
        reasons = [item.reason for item in AssignmentSelectionDetail.query.all()]
        assert any("indisponibilidade" in reason.lower() for reason in reasons)


def test_generation_respects_restrictions(app):
    with app.app_context():
        _, version = _month()
        team = _reference()
        military = _military(1, team=team)
        db.session.add(
            MilitaryRestriction(
                military_id=military.id,
                restriction_type="UNAVAILABLE",
                start_date=date(2026, 1, 1),
                thursday=True,
                reason="Teste",
            )
        )
        db.session.commit()

        ScheduleGenerator().generate_at_po(version)

        assert Assignment.query.filter_by(assignment_date=date(2026, 1, 1)).count() == 0
        assert AssignmentSelectionDetail.query.filter(AssignmentSelectionDetail.reason.contains("absoluta")).count() > 0


def test_candidate_selector_rest_exactly_eight_hours_is_allowed_and_less_is_excluded(app):
    with app.app_context():
        _, version = _month()
        patrols = _patrols(1)
        save_manual_assignment(version, patrols[0], date(2026, 1, 1), "AT3")
        context = build_generation_context(version)
        selector = CandidateSelector()

        at1 = selector.select(context, date(2026, 1, 2), "AT1", 1, 0)
        at2 = selector.select(context, date(2026, 1, 2), "AT2", 1, 0)

        assert not at1.selected
        assert at2.selected


def test_generation_is_deterministic_for_same_data(app):
    with app.app_context():
        _, version = _month()
        _patrols(9)

        first = ScheduleGenerator().generate_at_po(version)
        first_status = first.status
        first_created = [
            (item.assignment_date, item.code, item.military_id)
            for item in Assignment.query.order_by(Assignment.assignment_date, Assignment.code, Assignment.military_id).all()
        ]

        assert first_status in {"COMPLETED", "COMPLETED_WITH_WARNINGS"}
        second_created = [
            (item.assignment_date, item.code, item.military_id)
            for item in Assignment.query.order_by(Assignment.assignment_date, Assignment.code, Assignment.military_id).all()
        ]

        assert first_created == second_created


def test_generation_blocks_non_draft_version(app):
    with app.app_context():
        _, version = _month(status=ScheduleMonthStatus.PUBLISHED.value)
        _patrols(9)

        with pytest.raises(ScheduleGenerationError):
            ScheduleGenerator().generate_at_po(version)


def test_generation_routes_execute_and_show_detail(client, app):
    with app.app_context():
        _, version = _month()
        _patrols(9)
        version_id = version.id

    response = client.post(f"/escala/2026/1/versoes/{version_id}/gerar", follow_redirects=True)
    detail = client.get(f"/escala/2026/1/versoes/{version_id}/geracoes/1")

    assert response.status_code == 200
    assert detail.status_code == 200
    assert b"Execucao" in detail.data


def test_generation_runs_final_diagnostic(app):
    with app.app_context():
        _, version = _month()
        _patrols(9)

        run = ScheduleGenerator().generate_at_po(version)

        assert run.diagnostic_run_id is not None
        assert latest_generation_run(version.id).id == run.id


def test_priority_real_case_generation_with_five_teams_and_support_groups(app):
    with app.app_context():
        _, version = _month()
        patrols = []
        for index, team_code in enumerate(["A", "B", "C", "D", "E"], start=1):
            team = _reference(team_code)
            patrols.append(_military(index, team=team))
        sec = _military(20, FunctionalType.SEC.value)
        si = _military(21, FunctionalType.SI.value)
        manual, _ = save_manual_assignment(version, patrols[2], date(2026, 1, 1), "PO2")
        db.session.add(
            Unavailability(
                military_id=patrols[0].id,
                code="LF",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 1),
                is_full_day=True,
                status=UnavailabilityStatus.CONFIRMED.value,
                reason="Teste",
            )
        )
        db.session.add(
            MilitaryRestriction(
                military_id=patrols[1].id,
                restriction_type="UNAVAILABLE",
                start_date=date(2026, 1, 1),
                thursday=True,
                reason="Teste",
            )
        )
        db.session.commit()

        run = ScheduleGenerator().generate_at_po(version)

        db.session.refresh(manual)
        first_day_assignments = Assignment.query.filter_by(assignment_date=date(2026, 1, 1)).all()
        first_day_military_ids = {item.military_id for item in first_day_assignments}
        selected_support_ids = {
            detail.military_id
            for detail in AssignmentSelectionDetail.query.filter_by(is_selected=True).all()
            if detail.military and detail.military.functional_type in {FunctionalType.SEC.value, FunctionalType.SI.value}
        }

        assert manual.code == "PO2"
        assert manual.is_locked is True
        assert patrols[0].id not in first_day_military_ids
        assert patrols[1].id not in first_day_military_ids
        assert {sec.id, si.id}.intersection(selected_support_ids)
        assert run.total_unfilled > 0
        assert Assignment.query.filter(Assignment.code.in_(["PT", "FF", "FC"])).count() == 0
        assert run.diagnostic_run_id is not None
