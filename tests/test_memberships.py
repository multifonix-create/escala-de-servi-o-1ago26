from datetime import date

import pytest

from app.extensions import db
from app.models import FunctionalType, Military, MilitaryTeamHistory
from app.services import membership_service, military_service, team_service
from app.services.membership_service import MembershipServiceError
from app.services.military_service import MilitaryServiceError
from app.validators import validate_military_payload


def valid_payload(**overrides):
    payload = {
        "name": "Militar A",
        "nim": "100001",
        "functional_type": "PATRULHEIRO",
        "is_active": "1",
        "start_date": "2026-01-01",
        "end_date": "",
        "notes": "",
    }
    payload.update(overrides)
    return payload


def create_military(**overrides):
    validation = validate_military_payload(valid_payload(**overrides))
    assert validation.is_valid
    return military_service.create_military(validation.data)


def team(code: str):
    return team_service.get_team_by_code(code)


def test_patrol_military_can_be_associated_to_team(app):
    military = create_military()

    membership = membership_service.assign_military_to_team(
        military,
        team("A"),
        date(2026, 1, 1),
        "Colocacao inicial",
    )

    assert membership.id is not None
    assert military.current_team.code == "A"
    assert MilitaryTeamHistory.query.count() == 1


def test_non_patrol_military_cannot_be_associated_to_team(app):
    military = create_military(functional_type=FunctionalType.SEC.value)

    with pytest.raises(MembershipServiceError) as error:
        membership_service.assign_military_to_team(military, team("A"), date(2026, 1, 1))

    assert "military" in error.value.errors
    assert MilitaryTeamHistory.query.count() == 0


def test_military_cannot_have_two_current_memberships(app):
    military = create_military()
    membership_service.assign_military_to_team(military, team("A"), date(2026, 1, 1))

    with pytest.raises(MembershipServiceError):
        membership_service.assign_military_to_team(military, team("B"), date(2026, 2, 1))

    assert MilitaryTeamHistory.query.count() == 1


def test_military_team_change_preserves_history_with_inclusive_end_date(app):
    military = create_military()
    membership_service.assign_military_to_team(military, team("A"), date(2026, 1, 1))

    membership_service.change_military_team(military, team("B"), date(2026, 3, 10))
    history = membership_service.list_memberships_for_military(military.id)

    assert len(history) == 2
    assert history[0].team.code == "B"
    assert history[0].start_date == date(2026, 3, 10)
    assert history[0].end_date is None
    assert history[1].team.code == "A"
    assert history[1].end_date == date(2026, 3, 9)


def test_historical_team_can_be_resolved_by_date(app):
    military = create_military()
    membership_service.assign_military_to_team(military, team("A"), date(2026, 1, 1))
    membership_service.change_military_team(military, team("B"), date(2026, 3, 10))

    assert membership_service.get_team_for_military_on_date(military.id, date(2026, 3, 9)).code == "A"
    assert membership_service.get_team_for_military_on_date(military.id, date(2026, 3, 10)).code == "B"


def test_overlapping_historical_membership_is_blocked(app):
    military = create_military()
    membership_service.assign_military_to_team(military, team("A"), date(2026, 1, 1))
    membership_service.change_military_team(military, team("B"), date(2026, 3, 10))
    previous = membership_service.list_memberships_for_military(military.id)[1]

    with pytest.raises(MembershipServiceError):
        membership_service.update_membership(
            previous,
            date(2026, 1, 1),
            date(2026, 3, 15),
        )


def test_functional_type_change_is_blocked_when_current_team_exists(app):
    military = create_military()
    membership_service.assign_military_to_team(military, team("A"), date(2026, 1, 1))
    validation = validate_military_payload(
        valid_payload(functional_type=FunctionalType.SEC.value)
    )

    with pytest.raises(MilitaryServiceError) as error:
        military_service.update_military(military, validation.data)

    assert "functional_type" in error.value.errors
    assert db.session.get(Military, military.id).functional_type == FunctionalType.PATRULHEIRO.value


def test_team_change_rolls_back_on_commit_failure(app, monkeypatch):
    military = create_military()
    current = membership_service.assign_military_to_team(military, team("A"), date(2026, 1, 1))

    def fail_commit():
        raise RuntimeError("commit failed")

    monkeypatch.setattr(db.session, "commit", fail_commit)

    with pytest.raises(RuntimeError):
        membership_service.change_military_team(military, team("B"), date(2026, 2, 1))

    db.session.rollback()
    db.session.expire_all()
    assert db.session.get(MilitaryTeamHistory, current.id).end_date is None
    assert MilitaryTeamHistory.query.count() == 1


def test_association_routes(client):
    military = create_military()
    team_a = team("A")

    response = client.post(
        f"/militares/{military.id}/equipa/associar",
        data={
            "team_id": str(team_a.id),
            "start_date": "2026-01-01",
            "reason": "Colocacao inicial",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Equipa associada com sucesso.".encode() in response.data
    assert db.session.get(Military, military.id).current_team.code == "A"


def test_change_routes(client):
    military = create_military()
    membership_service.assign_military_to_team(military, team("A"), date(2026, 1, 1))

    response = client.post(
        f"/militares/{military.id}/equipa/mudar",
        data={
            "team_id": str(team("B").id),
            "start_date": "2026-02-01",
            "reason": "Alteracao real",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Equipa alterada com sucesso.".encode() in response.data
    assert db.session.get(Military, military.id).current_team.code == "B"


def test_history_route(client):
    military = create_military()
    membership_service.assign_military_to_team(military, team("A"), date(2026, 1, 1))

    response = client.get(f"/militares/{military.id}/historico-equipas")

    assert response.status_code == 200
    assert "Histórico de equipas".encode() in response.data
