from datetime import date, timedelta

import pytest

from app.models import TeamCycleReference
from app.services import cycle_calculator, team_service
from app.services.cycle_calculator import CycleCalculationError, MissingTeamReferenceError


def team(code: str):
    return team_service.get_team_by_code(code)


def create_reference(code="A", reference_date=date(2026, 1, 5), phase=1, valid_from=None):
    return cycle_calculator.create_team_cycle_reference(
        team(code),
        reference_date,
        phase,
        valid_from or reference_date,
        "Referência de teste",
    )


def test_monday_of_week_normalizes_each_requested_day():
    assert cycle_calculator.monday_of_week(date(2026, 1, 5)) == date(2026, 1, 5)
    assert cycle_calculator.monday_of_week(date(2026, 1, 6)) == date(2026, 1, 5)
    assert cycle_calculator.monday_of_week(date(2026, 1, 10)) == date(2026, 1, 5)
    assert cycle_calculator.monday_of_week(date(2026, 1, 11)) == date(2026, 1, 5)


@pytest.mark.parametrize(
    ("offset", "expected_phase"),
    [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 5),
        (5, 6),
        (6, 1),
        (-1, 6),
    ],
)
def test_phase_sequence_wraps_forward_and_backward(offset, expected_phase):
    target = date(2026, 1, 5) + timedelta(weeks=offset)

    assert cycle_calculator.calculate_phase(1, date(2026, 1, 5), target) == expected_phase


def test_cycle_continues_between_months_and_years():
    assert cycle_calculator.calculate_phase(6, date(2026, 12, 28), date(2027, 1, 5)) == 1
    assert cycle_calculator.calculate_phase(5, date(2026, 1, 26), date(2026, 2, 2)) == 6
    assert cycle_calculator.calculate_phase(1, date(2026, 4, 27), date(2026, 5, 4)) == 2


def test_cycle_handles_february_in_common_and_leap_years():
    assert cycle_calculator.calculate_phase(1, date(2026, 2, 2), date(2026, 2, 28)) == 4
    assert cycle_calculator.calculate_phase(1, date(2028, 2, 7), date(2028, 2, 29)) == 4


@pytest.mark.parametrize(
    ("phase", "day", "expected_code"),
    [
        (1, date(2026, 1, 10), "DS"),
        (1, date(2026, 1, 11), "DC"),
        (2, date(2026, 1, 9), "DS"),
        (3, date(2026, 1, 8), "DS"),
        (3, date(2026, 1, 9), "DC"),
        (4, date(2026, 1, 7), "DS"),
        (4, date(2026, 1, 8), "DC"),
        (5, date(2026, 1, 6), "DS"),
        (5, date(2026, 1, 7), "DC"),
        (6, date(2026, 1, 5), "DS"),
        (6, date(2026, 1, 6), None),
    ],
)
def test_ds_and_dc_for_each_phase(phase, day, expected_code):
    assert cycle_calculator.day_off_code_for_phase(phase, day) == expected_code


def test_dc_is_never_created_for_one_day_phases():
    for phase in (2, 6):
        codes = [
            cycle_calculator.day_off_code_for_phase(phase, date(2026, 1, 5) + timedelta(days=day))
            for day in range(7)
        ]
        assert codes.count("DS") == 1
        assert "DC" not in codes


def test_ds_precedes_dc_in_two_day_phases():
    for phase in (1, 3, 4, 5):
        codes = [
            cycle_calculator.day_off_code_for_phase(phase, date(2026, 1, 5) + timedelta(days=day))
            for day in range(7)
        ]
        assert codes.index("DS") + 1 == codes.index("DC")


def test_reference_can_be_created_and_used(app):
    reference = create_reference(phase=3)
    calculated_day = cycle_calculator.calculate_team_day(team("A"), date(2026, 1, 8))

    assert reference.id is not None
    assert calculated_day.phase == 3
    assert calculated_day.code == "DS"
    assert calculated_day.explanation.reference_id == reference.id


def test_invalid_phase_is_rejected(app):
    with pytest.raises(CycleCalculationError):
        cycle_calculator.create_team_cycle_reference(
            team("A"),
            date(2026, 1, 5),
            7,
            date(2026, 1, 5),
        )


def test_missing_reference_is_reported(app):
    with pytest.raises(MissingTeamReferenceError):
        cycle_calculator.calculate_team_day(team("A"), date(2026, 1, 5))


def test_future_reference_preserves_previous_period(app):
    previous = create_reference(phase=1)
    future = create_reference(
        phase=4,
        reference_date=date(2026, 2, 2),
        valid_from=date(2026, 2, 2),
    )

    assert previous.valid_until == date(2026, 2, 1)
    assert future.valid_until is None
    assert cycle_calculator.get_reference_for_team_on_date(team("A").id, date(2026, 1, 31)).id == previous.id
    assert cycle_calculator.get_reference_for_team_on_date(team("A").id, date(2026, 2, 2)).id == future.id


def test_overlapping_reference_is_blocked(app):
    create_reference(phase=1)

    with pytest.raises(CycleCalculationError):
        cycle_calculator.create_team_cycle_reference(
            team("A"),
            date(2025, 12, 29),
            2,
            date(2025, 12, 29),
        )

    assert TeamCycleReference.query.count() == 1


def test_references_are_independent_by_team(app):
    create_reference(code="A", phase=1)
    create_reference(code="B", phase=4)

    assert cycle_calculator.calculate_team_day(team("A"), date(2026, 1, 7)).phase == 1
    assert cycle_calculator.calculate_team_day(team("B"), date(2026, 1, 7)).phase == 4
    assert cycle_calculator.calculate_team_day(team("B"), date(2026, 1, 7)).code == "DS"


def test_calculation_is_deterministic(app):
    create_reference(phase=5)

    first = cycle_calculator.calculate_team_day(team("A"), date(2026, 4, 30))
    second = cycle_calculator.calculate_team_day(team("A"), date(2026, 4, 30))

    assert first == second


def test_preview_interval_is_limited(app):
    create_reference()

    with pytest.raises(CycleCalculationError):
        cycle_calculator.preview_team_cycle(
            team("A"),
            date(2026, 1, 1),
            date(2026, 5, 31),
        )


def test_real_priority_phase_six_then_phase_one_weekend(app):
    create_reference(reference_date=date(2026, 6, 29), phase=6)
    days = {
        current.day: cycle_calculator.calculate_team_day(team("A"), current).code
        for current in [
            date(2026, 6, 29),
            date(2026, 6, 30),
            date(2026, 7, 1),
            date(2026, 7, 2),
            date(2026, 7, 3),
            date(2026, 7, 4),
            date(2026, 7, 5),
            date(2026, 7, 11),
            date(2026, 7, 12),
        ]
    }

    assert days[29] == "DS"
    assert days[30] is None
    assert days[1] is None
    assert days[2] is None
    assert days[3] is None
    assert days[4] is None
    assert days[5] is None
    assert days[11] == "DS"
    assert days[12] == "DC"
