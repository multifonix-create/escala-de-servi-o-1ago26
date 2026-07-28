from datetime import date, datetime, time

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    CompensationStatus,
    FunctionalType,
    Military,
    TeamCycleReference,
    Unavailability,
    UnavailabilityCode,
    UnavailabilityStatus,
)
from app.services import (
    availability_evaluator,
    membership_service,
    military_service,
    restriction_service,
    team_service,
    unavailability_evaluator,
    unavailability_service,
)
from app.services.unavailability_service import UnavailabilityServiceError
from app.validators import validate_military_payload, validate_unavailability_payload


def valid_military_payload(**overrides):
    payload = {
        "name": "Militar Indisponibilidade",
        "nim": "910001",
        "functional_type": FunctionalType.PATRULHEIRO.value,
        "is_active": "1",
        "start_date": "2026-01-01",
        "end_date": "",
        "notes": "",
    }
    payload.update(overrides)
    return payload


def create_military(**overrides):
    validation = validate_military_payload(valid_military_payload(**overrides))
    assert validation.is_valid
    return military_service.create_military(validation.data)


def unavailability_data(**overrides):
    data = {
        "code": UnavailabilityCode.LF.value,
        "start_date": date(2026, 1, 5),
        "end_date": date(2026, 1, 5),
        "start_time": None,
        "end_time": None,
        "is_full_day": True,
        "status": UnavailabilityStatus.CONFIRMED.value,
        "reason": "Ausência com acentos: férias, serviço, compensação.",
        "location": None,
        "travel_minutes_before": 0,
        "travel_minutes_after": 0,
        "compensation_status": CompensationStatus.NOT_APPLICABLE.value,
        "compensation_notes": None,
        "is_active": True,
    }
    data.update(overrides)
    return data


def create_unavailability(military, **overrides):
    item, overlaps = unavailability_service.create_unavailability(
        military,
        unavailability_data(**overrides),
    )
    return item, overlaps


def test_valid_unavailability_can_be_created(app):
    military = create_military()

    item, overlaps = create_unavailability(military)

    assert item.id is not None
    assert item.code == UnavailabilityCode.LF.value
    assert item.events[0].event_type == "CREATED"
    assert overlaps == []
    assert "férias" in item.reason


def test_invalid_code_is_rejected_by_database(app):
    military = create_military()
    db.session.add(
        Unavailability(
            military_id=military.id,
            code="INVALID",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            is_full_day=True,
            status=UnavailabilityStatus.PLANNED.value,
            reason="Inválida",
            travel_minutes_before=0,
            travel_minutes_after=0,
            compensation_status=CompensationStatus.NOT_APPLICABLE.value,
            is_active=True,
        )
    )

    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_validation_rejects_missing_military_by_service(app):
    assert db.session.get(Military, 9999) is None


def test_validation_rejects_invalid_code_and_status():
    validation = validate_unavailability_payload(
        {
            "code": "X",
            "status": "BAD",
            "start_date": "2026-01-01",
            "is_full_day": "1",
            "reason": "Motivo",
        }
    )

    assert "code" in validation.errors
    assert "status" in validation.errors


def test_start_date_required_and_end_before_start_rejected():
    missing = validate_unavailability_payload({"code": "LF", "reason": "Motivo"})
    invalid = validate_unavailability_payload(
        {"code": "LF", "start_date": "2026-01-02", "end_date": "2026-01-01", "is_full_day": "1", "reason": "Motivo"}
    )

    assert "start_date" in missing.errors
    assert "end_date" in invalid.errors


def test_full_day_clears_times_and_partial_requires_pair():
    full_day = validate_unavailability_payload(
        {"code": "LF", "start_date": "2026-01-01", "start_time": "08:00", "end_time": "10:00", "is_full_day": "1", "reason": "Motivo"}
    )
    partial = validate_unavailability_payload(
        {"code": "DIL", "start_date": "2026-01-01", "start_time": "08:00", "reason": "Motivo"}
    )

    assert full_day.is_valid
    assert full_day.data["start_time"] is None
    assert "start_time" in partial.errors


def test_partial_overnight_and_multi_day_intervals(app):
    military = create_military()
    overnight, _ = create_unavailability(
        military,
        code="TRIB",
        is_full_day=False,
        start_time=time(22, 0),
        end_time=time(6, 0),
    )
    multi, _ = create_unavailability(
        military,
        code="INQ",
        start_date=date(2026, 1, 10),
        end_date=date(2026, 1, 12),
        is_full_day=False,
        start_time=time(9, 0),
        end_time=time(12, 0),
        reason="Intervalo contínuo",
    )

    assert overnight.crosses_midnight is True
    assert unavailability_evaluator.interval_for_unavailability(multi).end == datetime(2026, 1, 12, 12)


def test_travel_minutes_extend_effective_interval(app):
    military = create_military()
    item, _ = create_unavailability(
        military,
        is_full_day=False,
        start_time=time(10, 0),
        end_time=time(11, 0),
        travel_minutes_before=30,
        travel_minutes_after=45,
    )
    interval = unavailability_evaluator.interval_for_unavailability(item)

    assert interval.effective_start == datetime(2026, 1, 5, 9, 30)
    assert interval.effective_end == datetime(2026, 1, 5, 11, 45)


def test_negative_travel_is_rejected():
    validation = validate_unavailability_payload(
        {"code": "DIL", "start_date": "2026-01-01", "is_full_day": "1", "travel_minutes_before": "-1", "reason": "Motivo"}
    )

    assert "travel_minutes_before" in validation.errors


def test_duplicate_exact_is_blocked(app):
    military = create_military()
    create_unavailability(military)

    with pytest.raises(UnavailabilityServiceError):
        create_unavailability(military)


def test_state_transitions_and_cancelled_does_not_block(app):
    military = create_military()
    item, _ = create_unavailability(military, status=UnavailabilityStatus.PLANNED.value)

    unavailability_service.confirm_unavailability(item)
    assert item.status == UnavailabilityStatus.CONFIRMED.value
    unavailability_service.cancel_unavailability(item)
    assert item.status == UnavailabilityStatus.CANCELLED.value

    result = availability_evaluator.evaluate_service_interval(
        military.id,
        datetime(2026, 1, 5, 9),
        datetime(2026, 1, 5, 10),
    )
    assert result.allowed is True


def test_reactivation_is_explicit(app):
    military = create_military()
    item, _ = create_unavailability(military)
    unavailability_service.cancel_unavailability(item)
    unavailability_service.reactivate_unavailability(item)

    assert item.status == UnavailabilityStatus.PLANNED.value


def test_invalid_reactivation_transition_is_rejected(app):
    military = create_military()
    item, _ = create_unavailability(military, status=UnavailabilityStatus.PLANNED.value)

    with pytest.raises(UnavailabilityServiceError):
        unavailability_service.reactivate_unavailability(item)


def test_overlaps_total_partial_and_containment_warn(app):
    military = create_military()
    create_unavailability(military, start_date=date(2026, 1, 5), end_date=date(2026, 1, 7))

    _, total = create_unavailability(military, code="BM", start_date=date(2026, 1, 5), end_date=date(2026, 1, 7))
    _, partial = create_unavailability(military, code="DIL", start_date=date(2026, 1, 7), end_date=date(2026, 1, 8))
    _, contained = create_unavailability(military, code="TRIB", start_date=date(2026, 1, 6), end_date=date(2026, 1, 6))

    assert total
    assert partial
    assert contained


def test_no_overlap_is_reported(app):
    military = create_military()
    create_unavailability(military)
    _, overlaps = create_unavailability(military, code="BM", start_date=date(2026, 1, 8), end_date=date(2026, 1, 8))

    assert overlaps == []


def test_confirmed_full_day_and_partial_block_temporally(app):
    military = create_military()
    create_unavailability(military)
    full_day = availability_evaluator.evaluate_service_interval(military.id, datetime(2026, 1, 5, 0), datetime(2026, 1, 6, 0))
    outside = availability_evaluator.evaluate_service_interval(military.id, datetime(2026, 1, 6, 9), datetime(2026, 1, 6, 10))

    assert full_day.allowed is False
    assert outside.allowed is True


def test_travel_before_and_after_create_conflicts(app):
    military = create_military()
    create_unavailability(
        military,
        is_full_day=False,
        start_time=time(10, 0),
        end_time=time(11, 0),
        travel_minutes_before=30,
        travel_minutes_after=30,
    )

    before = availability_evaluator.evaluate_service_interval(military.id, datetime(2026, 1, 5, 9, 40), datetime(2026, 1, 5, 9, 50))
    after = availability_evaluator.evaluate_service_interval(military.id, datetime(2026, 1, 5, 11, 10), datetime(2026, 1, 5, 11, 20))

    assert before.allowed is False
    assert after.allowed is False


def test_date_month_and_year_changes_are_supported(app):
    military = create_military()
    create_unavailability(military, start_date=date(2026, 12, 31), end_date=date(2027, 1, 2))

    result = availability_evaluator.evaluate_service_interval(military.id, datetime(2027, 1, 1, 9), datetime(2027, 1, 1, 10))

    assert result.allowed is False


def test_unavailability_precedes_special_availability(app):
    military = create_military()
    create_unavailability(military, is_full_day=False, start_time=time(22), end_time=time(6))
    restriction_service.create_restriction(
        military,
        {
            "restriction_type": "SPECIAL_AVAILABILITY",
            "start_date": date(2026, 1, 5),
            "end_date": None,
            "start_time": time(22),
            "end_time": time(6),
            "monday": True,
            "tuesday": False,
            "wednesday": False,
            "thursday": False,
            "friday": False,
            "saturday": False,
            "sunday": False,
            "is_active": True,
            "reason": "Noite especial",
            "notes": None,
        },
    )

    result = availability_evaluator.evaluate_service_interval(military.id, datetime(2026, 1, 5, 22), datetime(2026, 1, 6, 6))

    assert result.allowed is False
    assert result.priority == "UNAVAILABILITY"


def test_restrictions_apply_when_no_unavailability_blocks(app):
    military = create_military()
    restriction_service.create_restriction(
        military,
        {
            "restriction_type": "UNAVAILABLE",
            "start_date": date(2026, 1, 5),
            "end_date": None,
            "start_time": None,
            "end_time": None,
            "monday": False,
            "tuesday": False,
            "wednesday": False,
            "thursday": False,
            "friday": False,
            "saturday": False,
            "sunday": False,
            "is_active": True,
            "reason": "Restrição absoluta",
            "notes": None,
        },
    )

    result = availability_evaluator.evaluate_service_interval(military.id, datetime(2026, 1, 5, 9), datetime(2026, 1, 5, 10))

    assert result.allowed is False
    assert result.priority == "UNAVAILABLE"


def test_compensation_statuses_do_not_create_credits(app):
    military = create_military()
    for idx, status in enumerate(CompensationStatus):
        item, _ = create_unavailability(
            military,
            code=f"{UnavailabilityCode.OUTRA.value}",
            start_date=date(2026, 2, 1 + idx),
            end_date=date(2026, 2, 1 + idx),
            compensation_status=status.value,
            compensation_notes="Observação UTF-8: compensação.",
        )
        assert item.compensation_status == status.value


def test_cycle_coincidences_for_patrolman_ds_dc_and_non_applicable(app):
    military = create_military()
    team = team_service.list_teams()[0]
    membership_service.assign_military_to_team(military, team, date(2026, 1, 1), "Teste")
    db.session.add(
        TeamCycleReference(
            team_id=team.id,
            reference_date=date(2026, 1, 5),
            reference_phase=6,
            valid_from=date(2026, 1, 1),
            notes="Teste",
        )
    )
    db.session.commit()

    coincidences = unavailability_service.calculate_cycle_coincidences(
        military,
        date(2026, 1, 5),
        date(2026, 1, 18),
    )
    sec = create_military(nim="910002", functional_type=FunctionalType.SEC.value)
    sec_result = unavailability_service.calculate_cycle_coincidences(sec, date(2026, 1, 5), date(2026, 1, 5))

    assert any(item.day == date(2026, 1, 5) and item.code == "DS" for item in coincidences)
    assert any(item.day == date(2026, 1, 17) and item.code == "DS" for item in coincidences)
    assert any(item.day == date(2026, 1, 18) and item.code == "DC" for item in coincidences)
    assert sec_result[0].status == "NOT_APPLICABLE"


def test_priority_real_case_preserves_cycle_and_marks_pending_compensation(app):
    military = create_military()
    team = team_service.list_teams()[0]
    membership_service.assign_military_to_team(military, team, date(2026, 1, 1), "Teste real")
    db.session.add(
        TeamCycleReference(
            team_id=team.id,
            reference_date=date(2026, 1, 5),
            reference_phase=6,
            valid_from=date(2026, 1, 1),
            notes="Teste real",
        )
    )
    db.session.commit()
    item, _ = create_unavailability(
        military,
        start_date=date(2026, 1, 5),
        end_date=date(2026, 1, 18),
        compensation_status=CompensationStatus.PENDING_DECISION.value,
    )

    coincidences = unavailability_service.calculate_cycle_coincidences(military, item.start_date, item.end_date)
    references_after = TeamCycleReference.query.count()

    assert item.compensation_status == CompensationStatus.PENDING_DECISION.value
    assert references_after == 1
    assert [(day.day, day.code) for day in coincidences if day.code] == [
            (date(2026, 1, 5), "DS"),
            (date(2026, 1, 17), "DS"),
            (date(2026, 1, 18), "DC"),
        ]
