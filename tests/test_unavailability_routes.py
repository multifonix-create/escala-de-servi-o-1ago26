from datetime import date

from app.models import FunctionalType
from app.services import military_service
from app.validators import validate_military_payload


def create_military():
    validation = validate_military_payload(
        {
            "name": "Militar Rotas",
            "nim": "920001",
            "functional_type": FunctionalType.PATRULHEIRO.value,
            "is_active": "1",
            "start_date": "2026-01-01",
            "end_date": "",
            "notes": "",
        }
    )
    assert validation.is_valid
    return military_service.create_military(validation.data)


def valid_form(**overrides):
    data = {
        "code": "LF",
        "status": "PLANNED",
        "start_date": "2026-01-05",
        "end_date": "2026-01-05",
        "is_full_day": "1",
        "reason": "Férias",
        "travel_minutes_before": "0",
        "travel_minutes_after": "0",
        "compensation_status": "NOT_APPLICABLE",
        "compensation_notes": "",
        "location": "",
    }
    data.update(overrides)
    return data


def test_empty_list_pages(client):
    response = client.get("/indisponibilidades")

    assert response.status_code == 200
    assert "Sem indisponibilidades".encode() in response.data


def test_military_unavailability_pages_and_create(client, app):
    military = create_military()

    assert client.get(f"/militares/{military.id}/indisponibilidades").status_code == 200
    assert client.get(f"/militares/{military.id}/indisponibilidades/nova").status_code == 200

    response = client.post(f"/militares/{military.id}/indisponibilidades/nova", data=valid_form())

    assert response.status_code == 302


def test_create_validation_message(client, app):
    military = create_military()

    response = client.post(
        f"/militares/{military.id}/indisponibilidades/nova",
        data=valid_form(code="INVALID"),
    )

    assert response.status_code == 400
    assert "código válido".encode() in response.data


def test_detail_edit_confirm_cancel_reactivate_and_tester(client, app):
    military = create_military()
    created = client.post(f"/militares/{military.id}/indisponibilidades/nova", data=valid_form())
    assert created.status_code == 302
    item_id = int(created.headers["Location"].rstrip("/").split("/")[-1])

    assert client.get(f"/militares/{military.id}/indisponibilidades/{item_id}").status_code == 200
    assert client.get(f"/militares/{military.id}/indisponibilidades/{item_id}/editar").status_code == 200
    assert client.post(f"/militares/{military.id}/indisponibilidades/{item_id}/editar", data=valid_form(reason="Atualizado")).status_code == 302
    assert client.post(f"/militares/{military.id}/indisponibilidades/{item_id}/confirmar").status_code == 302
    assert client.post(f"/militares/{military.id}/indisponibilidades/{item_id}/cancelar").status_code == 302
    assert client.post(f"/militares/{military.id}/indisponibilidades/{item_id}/reativar").status_code == 302
    assert client.get(f"/militares/{military.id}/indisponibilidades/testar").status_code == 200

    test_response = client.post(
        f"/militares/{military.id}/indisponibilidades/testar",
        data={
            "start_date": "2026-01-05",
            "start_time": "09:00",
            "end_date": "2026-01-05",
            "end_time": "10:00",
            "description": "AT2",
        },
    )

    assert test_response.status_code == 200
    assert b"Permitido" in test_response.data or b"Bloqueado" in test_response.data


def test_filters_404_and_wrong_methods(client, app):
    military = create_military()
    client.post(f"/militares/{military.id}/indisponibilidades/nova", data=valid_form())

    assert client.get("/indisponibilidades?code=LF&status=PLANNED&start_date=2026-01-01&end_date=2026-01-31").status_code == 200
    assert client.get("/militares/9999/indisponibilidades").status_code == 404
    assert client.get(f"/militares/{military.id}/indisponibilidades/9999").status_code == 404
    assert client.get(f"/militares/{military.id}/indisponibilidades/1/cancelar").status_code == 405


def test_military_detail_shows_unavailability_summary(client, app):
    military = create_military()
    client.post(f"/militares/{military.id}/indisponibilidades/nova", data=valid_form(start_date=date.today().isoformat(), end_date=date.today().isoformat()))

    response = client.get(f"/militares/{military.id}")

    assert response.status_code == 200
    assert "Indisponibilidades futuras".encode() in response.data
