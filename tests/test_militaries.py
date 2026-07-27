import pytest

from app.extensions import db
from app.models import Military
from app.services import military_service
from app.services.military_service import MilitaryServiceError
from app.validators import validate_military_payload


def valid_payload(**overrides):
    payload = {
        "name": "Militar A",
        "nim": "000123",
        "functional_type": "PATRULHEIRO",
        "is_active": "1",
        "start_date": "2026-01-01",
        "end_date": "",
        "notes": "Observação com acentos: João, Gonçalo e Lourinhã.",
    }
    payload.update(overrides)
    return payload


def create_valid_military(**overrides):
    validation = validate_military_payload(valid_payload(**overrides))
    assert validation.is_valid
    return military_service.create_military(validation.data)


def test_valid_military_can_be_created(app):
    military = create_valid_military()

    assert military.id is not None
    assert military.name == "Militar A"
    assert military.nim == "000123"
    assert military.is_active is True


def test_name_is_required():
    validation = validate_military_payload(valid_payload(name="   "))

    assert validation.errors["name"] == "O nome é obrigatório."


def test_nim_is_required():
    validation = validate_military_payload(valid_payload(nim="   "))

    assert validation.errors["nim"] == "O NIM é obrigatório."


def test_nim_must_be_unique(app):
    create_valid_military()

    validation = validate_military_payload(valid_payload(name="Militar B"))
    with pytest.raises(MilitaryServiceError) as error:
        military_service.create_military(validation.data)

    assert "nim" in error.value.errors


def test_nim_is_preserved_as_text(app):
    military = create_valid_military(nim="000045")

    assert military.nim == "000045"
    assert isinstance(military.nim, str)


def test_functional_type_must_be_valid():
    validation = validate_military_payload(valid_payload(functional_type="OPERACIONAL"))

    assert "functional_type" in validation.errors


def test_end_date_cannot_be_before_start_date():
    validation = validate_military_payload(
        valid_payload(start_date="2026-05-10", end_date="2026-05-09")
    )

    assert "end_date" in validation.errors


def test_notes_accept_utf8_characters(app):
    military = create_valid_military(notes="Serviço, Aplicação, João e Lourinhã.")

    assert "João" in military.notes
    assert "Lourinhã" in military.notes


def test_military_can_be_deactivated_and_record_is_preserved(app):
    military = create_valid_military()

    military_service.deactivate_military(military)

    assert Military.query.count() == 1
    assert Military.query.first().is_active is False


def test_military_can_be_activated(app):
    military = create_valid_military(is_active="")
    military_service.deactivate_military(military)

    military_service.activate_military(military)

    assert military.is_active is True


def test_empty_list_route(client):
    response = client.get("/militares")

    assert response.status_code == 200
    assert "Sem militares registados".encode() in response.data


def test_create_page_route(client):
    response = client.get("/militares/novo")

    assert response.status_code == 200
    assert "Novo militar".encode() in response.data


def test_create_valid_military_route(client):
    response = client.post("/militares/novo", data=valid_payload(), follow_redirects=True)

    assert response.status_code == 200
    assert "Militar criado com sucesso.".encode() in response.data
    assert Military.query.count() == 1


def test_create_invalid_military_route(client):
    response = client.post("/militares/novo", data=valid_payload(name=" "))

    assert response.status_code == 400
    assert "O nome é obrigatório.".encode() in response.data


def test_detail_route(client):
    military = create_valid_military()

    response = client.get(f"/militares/{military.id}")

    assert response.status_code == 200
    assert b"000123" in response.data


def test_missing_id_returns_404(client):
    response = client.get("/militares/999")

    assert response.status_code == 404


def test_edit_valid_military_route(client):
    military = create_valid_military()

    response = client.post(
        f"/militares/{military.id}/editar",
        data=valid_payload(name="Militar A Editado"),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Militar atualizado com sucesso.".encode() in response.data
    assert db.session.get(Military, military.id).name == "Militar A Editado"


def test_edit_duplicate_nim_route(client):
    first = create_valid_military()
    second = create_valid_military(name="Militar B", nim="000456")

    response = client.post(
        f"/militares/{second.id}/editar",
        data=valid_payload(name="Militar B", nim=first.nim),
    )

    assert response.status_code == 400
    assert "Já existe um militar com este NIM.".encode() in response.data


def test_deactivate_route(client):
    military = create_valid_military()

    response = client.post(f"/militares/{military.id}/desativar", follow_redirects=True)

    assert response.status_code == 200
    assert db.session.get(Military, military.id).is_active is False


def test_activate_route(client):
    military = create_valid_military(is_active="")
    military_service.deactivate_military(military)

    response = client.post(f"/militares/{military.id}/ativar", follow_redirects=True)

    assert response.status_code == 200
    assert db.session.get(Military, military.id).is_active is True


def test_wrong_http_methods_are_not_allowed(client):
    military = create_valid_military()

    assert client.get("/militares/novo").status_code == 200
    assert client.get(f"/militares/{military.id}/desativar").status_code == 405
    assert client.get(f"/militares/{military.id}/ativar").status_code == 405


def test_tests_use_in_memory_database(app):
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"
    assert db.engine.url.database == ":memory:"


def test_no_militaries_are_created_on_app_start(app):
    assert Military.query.count() == 0
