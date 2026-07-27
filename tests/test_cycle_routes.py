from datetime import date

from app.models import TeamCycleReference
from app.services import cycle_calculator, team_service


def team(code: str):
    return team_service.get_team_by_code(code)


def create_reference():
    return cycle_calculator.create_team_cycle_reference(
        team("A"),
        date(2026, 1, 5),
        1,
        date(2026, 1, 5),
        "Teste de rota",
    )


def test_cycle_overview_route_without_references(client):
    response = client.get("/ciclo?date=2026-01-05")

    assert response.status_code == 200
    assert "Sem referência".encode() in response.data


def test_cycle_configure_route(client):
    response = client.get("/ciclo/configurar")

    assert response.status_code == 200
    assert "Configurar referências".encode() in response.data


def test_team_cycle_route_without_reference(client):
    team_a = team("A")

    response = client.get(f"/equipas/{team_a.id}/ciclo")

    assert response.status_code == 200
    assert "ainda não possui referência".encode() in response.data


def test_new_reference_form_route(client):
    team_a = team("A")

    response = client.get(f"/equipas/{team_a.id}/ciclo/nova-referencia")

    assert response.status_code == 200
    assert "Nova referência do ciclo".encode() in response.data


def test_create_reference_route(client):
    team_a = team("A")

    response = client.post(
        f"/equipas/{team_a.id}/ciclo/nova-referencia",
        data={
            "reference_date": "2026-01-05",
            "reference_phase": "1",
            "valid_from": "2026-01-05",
            "notes": "Referência real configurada manualmente",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Referência do ciclo criada com sucesso.".encode() in response.data
    assert TeamCycleReference.query.count() == 1


def test_create_reference_route_rejects_invalid_phase(client):
    team_a = team("A")

    response = client.post(
        f"/equipas/{team_a.id}/ciclo/nova-referencia",
        data={
            "reference_date": "2026-01-05",
            "reference_phase": "0",
            "valid_from": "2026-01-05",
        },
    )

    assert response.status_code == 400
    assert "A fase deve estar entre 1 e 6.".encode() in response.data


def test_reference_history_route(client):
    reference = create_reference()

    response = client.get(f"/equipas/{reference.team_id}/ciclo/historico")

    assert response.status_code == 200
    assert "Histórico de referências".encode() in response.data
    assert b"2026-01-05" in response.data


def test_preview_route(client):
    reference = create_reference()

    response = client.get(
        f"/ciclo/pre-visualizar?team_id={reference.team_id}&start_date=2026-01-05&end_date=2026-01-11"
    )

    assert response.status_code == 200
    assert b"2026-01-10" in response.data
    assert b"DS" in response.data
    assert b"DC" in response.data


def test_preview_route_rejects_missing_reference(client):
    team_a = team("A")

    response = client.get(
        f"/ciclo/pre-visualizar?team_id={team_a.id}&start_date=2026-01-05&end_date=2026-01-11"
    )

    assert response.status_code == 200
    assert "referência válida".encode() in response.data


def test_unknown_team_returns_404(client):
    assert client.get("/equipas/999/ciclo").status_code == 404
    assert client.get("/equipas/999/ciclo/nova-referencia").status_code == 404


def test_wrong_http_methods_are_not_allowed(client):
    team_a = team("A")

    assert client.post("/ciclo").status_code == 405
    assert client.get(f"/equipas/{team_a.id}/ciclo/nova-referencia").status_code == 200
