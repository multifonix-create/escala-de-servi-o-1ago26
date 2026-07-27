import pytest
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import OFFICIAL_TEAM_CODES, Team
from app.services import team_service


def test_official_teams_are_available(app):
    teams = team_service.list_teams()

    assert [team.code for team in teams] == list(OFFICIAL_TEAM_CODES)
    assert [team.name for team in teams] == [f"Equipa {code}" for code in OFFICIAL_TEAM_CODES]
    assert all(team.is_active for team in teams)


def test_no_extra_teams_are_created(app):
    assert Team.query.count() == 5


def test_team_code_must_be_unique(app):
    db.session.add(Team(code="A", name="Equipa A duplicada", is_active=True))

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_team_name_must_be_unique(app):
    db.session.add(Team(code="B", name="Equipa A", is_active=True))

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_invalid_team_code_is_blocked(app):
    db.session.add(Team(code="Z", name="Equipa Z", is_active=True))

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_teams_list_route(client):
    response = client.get("/equipas")

    assert response.status_code == 200
    assert "Equipa A".encode() in response.data
    assert "Equipa E".encode() in response.data


def test_team_detail_route(client):
    team = team_service.get_team_by_code("A")

    response = client.get(f"/equipas/{team.id}")

    assert response.status_code == 200
    assert "Sem militares associados atualmente.".encode() in response.data
