from app.models import MilitaryRestriction
from app.services import military_service
from app.validators import validate_military_payload


def valid_military_payload(**overrides):
    payload = {
        "name": "Militar Rotas",
        "nim": "910001",
        "functional_type": "SEC",
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


def valid_restriction_payload(**overrides):
    payload = {
        "restriction_type": "UNAVAILABLE",
        "start_date": "2026-01-01",
        "end_date": "",
        "is_full_day": "1",
        "reason": "Restrição real configurada manualmente",
        "notes": "Notas com acentos: restrição, terça-feira.",
        "is_active": "1",
    }
    payload.update(overrides)
    return payload


def test_empty_restrictions_list_route(client):
    response = client.get("/restricoes")

    assert response.status_code == 200
    assert "Sem restrições registadas".encode() in response.data


def test_military_restrictions_empty_route(client):
    military = create_military()

    response = client.get(f"/militares/{military.id}/restricoes")

    assert response.status_code == 200
    assert "Sem restrições".encode() in response.data


def test_new_restriction_form_route(client):
    military = create_military()

    response = client.get(f"/militares/{military.id}/restricoes/nova")

    assert response.status_code == 200
    assert "Nova restrição".encode() in response.data


def test_create_restriction_route(client):
    military = create_military()

    response = client.post(
        f"/militares/{military.id}/restricoes/nova",
        data=valid_restriction_payload(),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Restrição criada com sucesso.".encode() in response.data
    assert MilitaryRestriction.query.count() == 1


def test_create_restriction_route_validation(client):
    military = create_military()

    response = client.post(
        f"/militares/{military.id}/restricoes/nova",
        data=valid_restriction_payload(restriction_type="INVALID"),
    )

    assert response.status_code == 400
    assert "Selecione um tipo de restrição válido.".encode() in response.data


def test_detail_and_edit_restriction_routes(client):
    military = create_military()
    client.post(
        f"/militares/{military.id}/restricoes/nova",
        data=valid_restriction_payload(),
    )
    restriction = MilitaryRestriction.query.one()

    detail = client.get(f"/militares/{military.id}/restricoes/{restriction.id}")
    edit = client.post(
        f"/militares/{military.id}/restricoes/{restriction.id}/editar",
        data=valid_restriction_payload(reason="Motivo atualizado"),
        follow_redirects=True,
    )

    assert detail.status_code == 200
    assert edit.status_code == 200
    assert "Restrição atualizada com sucesso.".encode() in edit.data


def test_activate_and_deactivate_routes(client):
    military = create_military()
    client.post(f"/militares/{military.id}/restricoes/nova", data=valid_restriction_payload())
    restriction = MilitaryRestriction.query.one()

    deactivate = client.post(
        f"/militares/{military.id}/restricoes/{restriction.id}/desativar",
        follow_redirects=True,
    )
    activate = client.post(
        f"/militares/{military.id}/restricoes/{restriction.id}/ativar",
        follow_redirects=True,
    )

    assert deactivate.status_code == 200
    assert activate.status_code == 200


def test_restriction_tester_route(client):
    military = create_military()
    client.post(f"/militares/{military.id}/restricoes/nova", data=valid_restriction_payload())

    response = client.post(
        f"/militares/{military.id}/restricoes/testar",
        data={
            "service_date": "2026-01-05",
            "start_time": "09:00",
            "end_time": "10:00",
            "description": "Teste manual",
        },
    )

    assert response.status_code == 200
    assert "Bloqueado".encode() in response.data


def test_unknown_ids_return_404(client):
    military = create_military()

    assert client.get("/militares/999/restricoes").status_code == 404
    assert client.get(f"/militares/{military.id}/restricoes/999").status_code == 404


def test_wrong_http_methods_are_not_allowed(client):
    military = create_military()

    assert client.get(f"/militares/{military.id}/restricoes/nova").status_code == 200
    assert client.get(f"/militares/{military.id}/restricoes/1/desativar").status_code == 405
