from datetime import date, datetime, time

import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import MilitaryRestriction, RestrictionType
from app.services import military_service, restriction_evaluator, restriction_service
from app.services.restriction_service import RestrictionServiceError
from app.validators import validate_military_payload, validate_restriction_payload


def valid_military_payload(**overrides):
    payload = {
        "name": "Militar Restrição",
        "nim": "900001",
        "functional_type": "PATRULHEIRO",
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


def restriction_data(**overrides):
    data = {
        "restriction_type": RestrictionType.UNAVAILABLE.value,
        "start_date": date(2026, 1, 1),
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
        "reason": "Restrição de teste",
        "notes": "Observação com acentos: serviço, João, terça-feira.",
    }
    data.update(overrides)
    return data


def create_restriction(military, **overrides):
    return restriction_service.create_restriction(
        military,
        restriction_data(**overrides),
    )


def evaluate(military, start, end):
    return restriction_evaluator.evaluate_service_interval(military.id, start, end)


def test_valid_restriction_can_be_created(app):
    military = create_military()

    restriction = create_restriction(military)

    assert restriction.id is not None
    assert restriction.restriction_type == RestrictionType.UNAVAILABLE.value
    assert restriction.is_full_day is True
    assert "João" in restriction.notes


def test_invalid_restriction_type_is_rejected_by_database(app):
    military = create_military()
    db.session.add(
        MilitaryRestriction(
            military_id=military.id,
            restriction_type="INVALID",
            start_date=date(2026, 1, 1),
            is_active=True,
            reason="Inválida",
        )
    )

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_start_date_is_required():
    validation = validate_restriction_payload(
        {
            "restriction_type": RestrictionType.UNAVAILABLE.value,
            "start_date": "",
            "is_full_day": "1",
            "reason": "Motivo",
        }
    )

    assert "start_date" in validation.errors


def test_end_date_cannot_be_before_start_date():
    validation = validate_restriction_payload(
        {
            "restriction_type": RestrictionType.UNAVAILABLE.value,
            "start_date": "2026-01-02",
            "end_date": "2026-01-01",
            "is_full_day": "1",
            "reason": "Motivo",
        }
    )

    assert "end_date" in validation.errors


def test_restriction_without_times_can_be_full_day():
    validation = validate_restriction_payload(
        {
            "restriction_type": RestrictionType.UNAVAILABLE.value,
            "start_date": "2026-01-01",
            "is_full_day": "1",
            "reason": "Motivo",
        }
    )

    assert validation.is_valid
    assert validation.data["start_time"] is None
    assert validation.data["end_time"] is None


def test_only_one_time_fails_validation():
    validation = validate_restriction_payload(
        {
            "restriction_type": RestrictionType.UNAVAILABLE.value,
            "start_date": "2026-01-01",
            "start_time": "08:00",
            "reason": "Motivo",
        }
    )

    assert "start_time" in validation.errors


def test_normal_and_overnight_intervals_are_supported(app):
    military = create_military()
    normal = create_restriction(
        military,
        start_time=time(8, 0),
        end_time=time(14, 0),
    )
    overnight = create_restriction(
        military,
        restriction_type=RestrictionType.SPECIAL_AVAILABILITY.value,
        start_time=time(22, 0),
        end_time=time(6, 0),
        thursday=True,
        reason="Noite específica",
    )

    assert normal.crosses_midnight is False
    assert overnight.crosses_midnight is True


def test_deactivate_and_reactivate_restriction(app):
    military = create_military()
    restriction = create_restriction(military)

    restriction_service.deactivate_restriction(restriction)
    assert restriction.is_active is False

    restriction_service.activate_restriction(restriction)
    assert restriction.is_active is True


def test_no_weekday_selected_applies_to_all_days(app):
    military = create_military()
    create_restriction(military)

    monday = evaluate(military, datetime(2026, 1, 5, 9), datetime(2026, 1, 5, 10))
    saturday = evaluate(military, datetime(2026, 1, 10, 9), datetime(2026, 1, 10, 10))

    assert monday.allowed is False
    assert saturday.allowed is False


def test_selected_weekdays_are_respected(app):
    military = create_military()
    create_restriction(military, monday=True)

    monday = evaluate(military, datetime(2026, 1, 5, 9), datetime(2026, 1, 5, 10))
    tuesday = evaluate(military, datetime(2026, 1, 6, 9), datetime(2026, 1, 6, 10))

    assert monday.allowed is False
    assert tuesday.allowed is True


def test_weekend_pattern_is_supported(app):
    military = create_military()
    create_restriction(military, saturday=True, sunday=True)

    saturday = evaluate(military, datetime(2026, 1, 10, 9), datetime(2026, 1, 10, 10))
    monday = evaluate(military, datetime(2026, 1, 12, 9), datetime(2026, 1, 12, 10))

    assert saturday.allowed is False
    assert monday.allowed is True


def test_unavailable_total_and_partial_overlap_blocks(app):
    military = create_military()
    create_restriction(
        military,
        start_time=time(8, 0),
        end_time=time(12, 0),
    )

    assert evaluate(military, datetime(2026, 1, 5, 8), datetime(2026, 1, 5, 12)).allowed is False
    assert evaluate(military, datetime(2026, 1, 5, 11), datetime(2026, 1, 5, 13)).allowed is False
    assert evaluate(military, datetime(2026, 1, 5, 13), datetime(2026, 1, 5, 14)).allowed is True


def test_date_outside_validity_allows_service(app):
    military = create_military()
    create_restriction(
        military,
        start_date=date(2026, 1, 10),
        end_date=date(2026, 1, 12),
    )

    result = evaluate(military, datetime(2026, 1, 9, 9), datetime(2026, 1, 9, 10))

    assert result.allowed is True


def test_available_only_contains_service_to_allow(app):
    military = create_military()
    create_restriction(
        military,
        restriction_type=RestrictionType.AVAILABLE_ONLY.value,
        start_time=time(8, 0),
        end_time=time(14, 0),
    )

    assert evaluate(military, datetime(2026, 1, 5, 8), datetime(2026, 1, 5, 14)).allowed is True
    assert evaluate(military, datetime(2026, 1, 5, 7), datetime(2026, 1, 5, 10)).allowed is False
    assert evaluate(military, datetime(2026, 1, 5, 13), datetime(2026, 1, 5, 15)).allowed is False
    assert evaluate(military, datetime(2026, 1, 5, 15), datetime(2026, 1, 5, 16)).allowed is False


def test_available_only_blocks_day_outside_pattern(app):
    military = create_military()
    create_restriction(
        military,
        restriction_type=RestrictionType.AVAILABLE_ONLY.value,
        start_time=time(8, 0),
        end_time=time(14, 0),
        monday=True,
    )

    assert evaluate(military, datetime(2026, 1, 6, 9), datetime(2026, 1, 6, 10)).allowed is False


def test_multiple_available_windows_allow_either_window(app):
    military = create_military()
    create_restriction(
        military,
        restriction_type=RestrictionType.AVAILABLE_ONLY.value,
        start_time=time(8, 0),
        end_time=time(12, 0),
        reason="Manhã",
    )
    create_restriction(
        military,
        restriction_type=RestrictionType.AVAILABLE_ONLY.value,
        start_time=time(14, 0),
        end_time=time(18, 0),
        reason="Tarde",
    )

    assert evaluate(military, datetime(2026, 1, 5, 15), datetime(2026, 1, 5, 16)).allowed is True
    assert evaluate(military, datetime(2026, 1, 5, 12), datetime(2026, 1, 5, 14)).allowed is False


def test_special_availability_authorizes_only_specific_interval(app):
    military = create_military()
    create_restriction(
        military,
        restriction_type=RestrictionType.AVAILABLE_ONLY.value,
        start_time=time(8, 0),
        end_time=time(14, 0),
    )
    create_restriction(
        military,
        restriction_type=RestrictionType.SPECIAL_AVAILABILITY.value,
        start_time=time(22, 0),
        end_time=time(6, 0),
        thursday=True,
        reason="Noite autorizada",
    )

    authorized = evaluate(military, datetime(2026, 1, 8, 22), datetime(2026, 1, 9, 6))
    other_night = evaluate(military, datetime(2026, 1, 9, 22), datetime(2026, 1, 10, 6))

    assert authorized.allowed is True
    assert authorized.decision == "ALLOWED_BY_SPECIAL_AVAILABILITY"
    assert other_night.allowed is False


def test_unavailable_prevents_special_availability(app):
    military = create_military()
    create_restriction(
        military,
        restriction_type=RestrictionType.UNAVAILABLE.value,
        start_time=time(22, 0),
        end_time=time(6, 0),
        thursday=True,
        reason="Bloqueio absoluto",
    )
    create_restriction(
        military,
        restriction_type=RestrictionType.SPECIAL_AVAILABILITY.value,
        start_time=time(22, 0),
        end_time=time(6, 0),
        thursday=True,
        reason="Exceção",
    )

    result = evaluate(military, datetime(2026, 1, 8, 22), datetime(2026, 1, 9, 6))

    assert result.allowed is False
    assert result.priority == "UNAVAILABLE"


def test_same_input_produces_same_result(app):
    military = create_military()
    create_restriction(
        military,
        restriction_type=RestrictionType.AVAILABLE_ONLY.value,
        start_time=time(8, 0),
        end_time=time(14, 0),
    )

    first = evaluate(military, datetime(2026, 1, 5, 9), datetime(2026, 1, 5, 10))
    second = evaluate(military, datetime(2026, 1, 5, 9), datetime(2026, 1, 5, 10))

    assert first == second


def test_duplicate_exact_restriction_is_blocked(app):
    military = create_military()
    create_restriction(military)

    with pytest.raises(RestrictionServiceError):
        create_restriction(military)


def test_real_priority_general_day_availability_and_specific_night(app):
    military = create_military()
    create_restriction(
        military,
        restriction_type=RestrictionType.AVAILABLE_ONLY.value,
        start_time=time(8, 0),
        end_time=time(14, 0),
        reason="Disponível apenas de dia",
    )
    create_restriction(
        military,
        restriction_type=RestrictionType.SPECIAL_AVAILABILITY.value,
        start_time=time(22, 0),
        end_time=time(6, 0),
        thursday=True,
        reason="Noite de quinta para sexta",
    )

    day_inside = evaluate(military, datetime(2026, 1, 8, 9), datetime(2026, 1, 8, 12))
    day_outside = evaluate(military, datetime(2026, 1, 8, 15), datetime(2026, 1, 8, 16))
    special_night = evaluate(military, datetime(2026, 1, 8, 22), datetime(2026, 1, 9, 6))
    other_night = evaluate(military, datetime(2026, 1, 9, 22), datetime(2026, 1, 10, 6))

    assert day_inside.allowed is True
    assert day_outside.allowed is False
    assert special_night.allowed is True
    assert other_night.allowed is False
