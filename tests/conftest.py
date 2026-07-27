import pytest

from app import create_app
from app.extensions import db
from app.models import OFFICIAL_TEAM_CODES, Team


@pytest.fixture()
def app():
    app = create_app("testing")

    with app.app_context():
        db.create_all()
        _seed_official_teams_for_tests()
        yield app
        db.session.remove()


@pytest.fixture()
def client(app):
    return app.test_client()


def _seed_official_teams_for_tests() -> None:
    for code in OFFICIAL_TEAM_CODES:
        db.session.add(Team(code=code, name=f"Equipa {code}", is_active=True))
    db.session.commit()
