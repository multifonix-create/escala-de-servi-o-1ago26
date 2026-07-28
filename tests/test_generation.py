from datetime import date

import pytest

from app.extensions import db
from app.models import (
    Assignment,
    AssignmentChange,
    AssignmentSelectionDetail,
    FunctionalType,
    GenerationMode,
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
from app.services.assignment_service import clear_assignment, save_manual_assignment, unlock_assignment
from app.services.schedule_generator import (
    CandidateSelector,
    ScheduleGenerationError,
    ScheduleGenerator,
    build_generation_context,
    latest_generation_run,
)
from app.services.schedule_regeneration import (
    ScheduleRegenerationError,
    ScheduleRegenerationService,
    compare_versions,
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


def test_regeneration_creates_new_version_and_preserves_source(app):
    with app.app_context():
        schedule_month, version = _month()
        patrols = _patrols(9)
        manual, _ = save_manual_assignment(version, patrols[0], date(2026, 1, 1), "PO2")
        first_run = ScheduleGenerator().generate_at_po(version)
        original_assignment_ids = {item.id for item in version.assignments}

        summary = ScheduleRegenerationService().regenerate_automatic_at_po(version)
        result_version = db.session.get(ScheduleVersion, summary.result_version_id)

        assert result_version.version_number == 2
        assert result_version.parent_version_id == version.id
        assert result_version.source == ScheduleVersionSource.SYSTEM.value
        assert result_version.status == ScheduleMonthStatus.DRAFT.value
        assert result_version.generation_mode == GenerationMode.REGENERATE_AUTOMATIC.value
        assert {item.id for item in version.assignments} == original_assignment_ids
        assert Assignment.query.filter_by(schedule_version_id=result_version.id, source="MANUAL").count() == 1
        assert Assignment.query.filter_by(schedule_version_id=result_version.id, source="SYSTEM").count() > 0
        assert first_run.result_version_id == version.id
        assert manual.schedule_version_id == version.id


def test_regeneration_does_not_copy_old_automatic_assignments(app):
    with app.app_context():
        _, version = _month()
        _patrols(9)
        ScheduleGenerator().generate_at_po(version)
        old_system_ids = {item.id for item in Assignment.query.filter_by(schedule_version_id=version.id, source="SYSTEM").all()}

        summary = ScheduleRegenerationService().regenerate_automatic_at_po(version)
        result_system_ids = {item.id for item in Assignment.query.filter_by(schedule_version_id=summary.result_version_id, source="SYSTEM").all()}

        assert old_system_ids
        assert result_system_ids
        assert old_system_ids.isdisjoint(result_system_ids)


def test_regeneration_preserves_unlocked_manual_notes_override_and_ignores_cleared(app):
    with app.app_context():
        _, version = _month()
        patrols = _patrols(9)
        manual, _ = save_manual_assignment(version, patrols[0], date(2026, 1, 1), "PO2", notes="Nota manual")
        unlock_assignment(manual, "Teste")
        cleared, _ = save_manual_assignment(version, patrols[1], date(2026, 1, 2), "PO2")
        unlock_assignment(cleared, "Teste")
        clear_assignment(cleared, "Limpeza")
        ScheduleGenerator().generate_at_po(version)

        summary = ScheduleRegenerationService().regenerate_automatic_at_po(version)
        copied = Assignment.query.filter_by(
            schedule_version_id=summary.result_version_id,
            military_id=manual.military_id,
            assignment_date=manual.assignment_date,
            source="MANUAL",
        ).one()

        assert copied.code == "PO2"
        assert copied.is_locked is False
        assert copied.notes == "Nota manual"
        assert copied.changes[0].change_type == "CREATED"
        assert "Copiada da versao" in copied.changes[0].reason
        assert Assignment.query.filter_by(
            schedule_version_id=summary.result_version_id,
            military_id=cleared.military_id,
            assignment_date=cleared.assignment_date,
            source="MANUAL",
        ).count() == 0


def test_regeneration_blocks_published_and_closed_versions(app):
    with app.app_context():
        _, published = _month(status=ScheduleMonthStatus.PUBLISHED.value)
        with pytest.raises(ScheduleRegenerationError):
            ScheduleRegenerationService().regenerate_automatic_at_po(published)

    with app.app_context():
        _, closed = _month(year=2026, month=2, status=ScheduleMonthStatus.CLOSED.value)
        with pytest.raises(ScheduleRegenerationError):
            ScheduleRegenerationService().regenerate_automatic_at_po(closed)


def test_regeneration_allows_validated_as_new_draft_version(app):
    with app.app_context():
        _, version = _month(status=ScheduleMonthStatus.VALIDATED.value)
        _patrols(9)

        summary = ScheduleRegenerationService().regenerate_automatic_at_po(version)
        result_version = db.session.get(ScheduleVersion, summary.result_version_id)

        assert result_version.status == ScheduleMonthStatus.DRAFT.value
        assert result_version.parent_version_id == version.id


def test_regeneration_rolls_back_new_version_on_failure(app):
    class FailingGenerator:
        def generate_into_version(self, schedule_version, run, commit=True):
            raise RuntimeError("falha controlada")

    with app.app_context():
        _, version = _month()
        patrols = _patrols(1)
        save_manual_assignment(version, patrols[0], date(2026, 1, 1), "PO2")
        before_versions = ScheduleVersion.query.count()
        before_assignments = Assignment.query.count()

        with pytest.raises(ScheduleRegenerationError):
            ScheduleRegenerationService(generator=FailingGenerator()).regenerate_automatic_at_po(version)

        assert ScheduleVersion.query.count() == before_versions
        assert Assignment.query.count() == before_assignments
        assert GenerationRun.query.count() == 0


def test_version_comparison_reports_preserved_manual_and_automatic_changes(app):
    with app.app_context():
        _, version = _month()
        patrols = _patrols(9)
        save_manual_assignment(version, patrols[0], date(2026, 1, 1), "PO2")
        ScheduleGenerator().generate_at_po(version)

        summary = ScheduleRegenerationService().regenerate_automatic_at_po(version)
        comparison = compare_versions(version, db.session.get(ScheduleVersion, summary.result_version_id))

        assert comparison.preserved_manual == 1
        assert comparison.removed_automatic > 0
        assert comparison.created_automatic > 0
        assert comparison.total_differences >= comparison.created_automatic


def test_regeneration_routes_confirm_execute_and_compare(client, app):
    with app.app_context():
        _, version = _month()
        _patrols(9)
        ScheduleGenerator().generate_at_po(version)
        version_id = version.id

    confirm = client.get(f"/escala/2026/1/versoes/{version_id}/regenerar")
    blocked = client.post(f"/escala/2026/1/versoes/{version_id}/regenerar", follow_redirects=True)
    executed = client.post(
        f"/escala/2026/1/versoes/{version_id}/regenerar",
        data={"confirm_regeneration": "on"},
        follow_redirects=True,
    )

    assert confirm.status_code == 200
    assert blocked.status_code == 200
    assert b"Confirme" in blocked.data
    assert executed.status_code == 200
    assert b"Comparacao" in executed.data


def test_priority_real_case_regeneration_excludes_new_unavailability_and_preserves_version_one(app):
    with app.app_context():
        _, version = _month()
        patrols = _patrols(12)
        manual, _ = save_manual_assignment(version, patrols[0], date(2026, 1, 1), "PO2")
        ScheduleGenerator().generate_at_po(version)
        old_system = Assignment.query.filter_by(
            schedule_version_id=version.id,
            assignment_date=date(2026, 1, 1),
            source="SYSTEM",
        ).first()
        db.session.add(
            Unavailability(
                military_id=old_system.military_id,
                code="LF",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 1, 1),
                is_full_day=True,
                status=UnavailabilityStatus.CONFIRMED.value,
                reason="Posterior",
            )
        )
        db.session.commit()

        summary = ScheduleRegenerationService().regenerate_automatic_at_po(version)
        result_version = db.session.get(ScheduleVersion, summary.result_version_id)
        result_first_day_ids = {
            item.military_id
            for item in Assignment.query.filter_by(schedule_version_id=result_version.id, assignment_date=date(2026, 1, 1)).all()
        }

        assert old_system.military_id not in result_first_day_ids
        assert Assignment.query.filter_by(schedule_version_id=version.id, id=old_system.id).count() == 1
        assert Assignment.query.filter_by(schedule_version_id=result_version.id, source="MANUAL").count() == 1
        assert manual.schedule_version_id == version.id
        assert GenerationRun.query.filter_by(result_version_id=result_version.id).one().diagnostic_run_id is not None
        assert Assignment.query.filter(Assignment.code.in_(["PT", "FF", "FC"])).count() == 0
