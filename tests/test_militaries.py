from datetime import date

import pytest

from app.extensions import db
from app.models import Military
from app.services import military_service
from app.services.military_service import MilitaryServiceError
from app.validators import validate_military_payload


def valid_payload(**overrides):
    payload = {
        "first_name": "Militar",
        "last_name": "A",
        "nim": "000123",
        "phone_number": "912 345 678",
        "functional_type": "PATRULHEIRO",
        "team_id": "1",
        "is_paid_service_volunteer": "",
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
    assert military.full_name == "Militar A"
    assert military.nim == "000123"
    assert military.phone_number == "+351912345678"
    assert military.current_team.code == "A"
    assert military.is_active is True


def test_first_name_is_required():
    validation = validate_military_payload(valid_payload(first_name="   "))

    assert validation.errors["first_name"] == "O nome é obrigatório."


def test_last_name_is_required():
    validation = validate_military_payload(valid_payload(last_name="   "))

    assert validation.errors["last_name"] == "O sobrenome é obrigatório."


def test_phone_number_is_required():
    validation = validate_military_payload(valid_payload(phone_number="   "))

    assert validation.errors["phone_number"] == "O contacto é obrigatório."


def test_nim_is_required():
    validation = validate_military_payload(valid_payload(nim="   "))

    assert validation.errors["nim"] == "O NIM é obrigatório."


def test_nim_must_be_unique(app):
    create_valid_military()

    validation = validate_military_payload(valid_payload(last_name="B"))
    with pytest.raises(MilitaryServiceError) as error:
        military_service.create_military(validation.data)

    assert "nim" in error.value.errors


def test_nim_is_preserved_as_text(app):
    military = create_valid_military(nim="000045")

    assert military.nim == "000045"
    assert isinstance(military.nim, str)


def test_nim_must_contain_only_digits():
    validation = validate_military_payload(valid_payload(nim="00A045"))

    assert "nim" in validation.errors


def test_phone_number_accepts_country_prefix(app):
    validation = validate_military_payload(valid_payload(phone_number="+351912345678"))

    assert validation.is_valid
    assert validation.data["phone_number"] == "+351912345678"


def test_functional_type_must_be_valid():
    validation = validate_military_payload(valid_payload(functional_type="OPERACIONAL"))

    assert "functional_type" in validation.errors


def test_patrol_requires_team():
    validation = validate_military_payload(valid_payload(team_id=""))

    assert validation.errors["team_id"] == "Patrulheiro exige equipa operacional A-E."


def test_sec_does_not_accept_operational_team():
    validation = validate_military_payload(valid_payload(functional_type="SEC", team_id=""))
    assert validation.is_valid

    validation = validate_military_payload(valid_payload(functional_type="SEC", team_id="1"))
    assert "team_id" in validation.errors


def test_end_date_cannot_be_before_start_date():
    validation = validate_military_payload(
        valid_payload(start_date="2026-05-10", end_date="2026-05-09")
    )

    assert "end_date" in validation.errors


def test_notes_accept_utf8_characters(app):
    military = create_valid_military(notes="Serviço, Aplicação, João e Lourinhã.")

    assert "João" in military.notes
    assert "Lourinhã" in military.notes


def test_paid_service_volunteer_flag_is_stored(app):
    military = create_valid_military(is_paid_service_volunteer="1")

    assert military.is_paid_service_volunteer is True
    assert military.paid_service_volunteer_label == "Sim"


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
    response = client.post("/militares/novo", data=valid_payload(first_name=" "))

    assert response.status_code == 400
    assert "O nome é obrigatório.".encode() in response.data


def test_detail_route(client):
    military = create_valid_military()

    response = client.get(f"/militares/{military.id}")

    assert response.status_code == 200
    assert b"000123" in response.data
    assert "Serviços remunerados".encode() in response.data


def test_missing_id_returns_404(client):
    response = client.get("/militares/999")

    assert response.status_code == 404


def test_edit_valid_military_route(client):
    military = create_valid_military()

    response = client.post(
        f"/militares/{military.id}/editar",
        data=valid_payload(first_name="Militar", last_name="Editado"),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Militar atualizado com sucesso.".encode() in response.data
    assert db.session.get(Military, military.id).full_name == "Militar Editado"


def test_edit_duplicate_nim_route(client):
    first = create_valid_military()
    second = create_valid_military(last_name="B", nim="000456")

    response = client.post(
        f"/militares/{second.id}/editar",
        data=valid_payload(last_name="B", nim=first.nim),
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


def test_save_and_add_restriction_redirects_to_existing_restriction_form(client):
    response = client.post(
        "/militares/novo",
        data=valid_payload(action="save_and_add_restriction"),
    )

    assert response.status_code == 302
    assert "/restricoes/nova" in response.headers["Location"]


def test_legacy_name_remains_display_fallback(app):
    legacy = Military(
        name="Nome Legado",
        nim="999001",
        functional_type="SEC",
        start_date=date(2026, 1, 1),
    )
    db.session.add(legacy)
    db.session.commit()

    assert legacy.full_name == "Nome Legado"
