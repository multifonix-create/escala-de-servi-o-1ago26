from pathlib import Path

from app.extensions import db


def test_application_factory_creates_app(app):
    assert app is not None
    assert app.config["TESTING"] is True
    assert app.config["APP_VERSION"] == "v1.9"


def test_index_page_responds_successfully(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "Escala de Serviço".encode() in response.data
    assert b"v1.9" in response.data


def test_health_route_responds_successfully(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "application": "Escala de Serviço",
        "status": "ok",
        "version": "v1.9",
    }


def test_testing_database_is_independent(app):
    configured_database = db.engine.url.database
    real_database = Path(app.root_path).parent / "instance" / "escala.db"

    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
    assert configured_database != str(real_database)
