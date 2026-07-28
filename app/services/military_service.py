from sqlalchemy import func, or_

from app.extensions import db
from app.models import FunctionalType, Military, MilitaryTeamHistory, Team


class MilitaryServiceError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__("Dados de militar inválidos.")
        self.errors = errors


def list_militaries(
    status: str | None = None,
    functional_type: str | None = None,
    query: str | None = None,
    team_id: int | None = None,
    without_team: bool = False,
) -> list[Military]:
    statement = Military.query

    if status == "active":
        statement = statement.filter(Military.is_active.is_(True))
    elif status == "inactive":
        statement = statement.filter(Military.is_active.is_(False))

    if functional_type:
        statement = statement.filter(Military.functional_type == functional_type)

    if query:
        search = f"%{query.strip()}%"
        statement = statement.filter(
            or_(
                Military.name.ilike(search),
                Military.first_name.ilike(search),
                Military.last_name.ilike(search),
                Military.nim.ilike(search),
            )
        )

    militaries = statement.order_by(Military.name.asc(), Military.nim.asc()).all()

    if team_id is not None:
        militaries = [
            military
            for military in militaries
            if military.current_team is not None and military.current_team.id == team_id
        ]
    elif without_team:
        militaries = [
            military
            for military in militaries
            if military.functional_type == "PATRULHEIRO" and military.current_team is None
        ]

    return militaries


def count_militaries() -> dict[str, int]:
    total = db.session.scalar(db.select(func.count(Military.id))) or 0
    active = (
        db.session.scalar(
            db.select(func.count(Military.id)).where(Military.is_active.is_(True))
        )
        or 0
    )
    inactive = total - active
    return {"total": total, "active": active, "inactive": inactive}


def get_military_or_404(military_id: int) -> Military:
    return db.get_or_404(Military, military_id)


def create_military(data: dict) -> Military:
    payload = dict(data)
    team_supplied = "team_id" in payload
    team_id = payload.pop("team_id", None)
    _raise_for_duplicate_nim(payload["nim"])
    team = _get_valid_team(team_id) if team_id else None
    if team_supplied:
        _raise_for_missing_or_invalid_team(payload["functional_type"], team)
    military = Military(**payload)
    military.sync_name_from_parts()
    try:
        db.session.add(military)
        db.session.flush()
        _upsert_current_team(military, team, military.start_date)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return military


def update_military(military: Military, data: dict) -> Military:
    payload = dict(data)
    team_supplied = "team_id" in payload
    team_id = payload.pop("team_id", None)
    _raise_for_duplicate_nim(payload["nim"], excluded_id=military.id)
    _raise_for_invalid_functional_type_change(military, payload["functional_type"])
    team = _get_valid_team(team_id) if team_id else None
    if team_supplied:
        _raise_for_missing_or_invalid_team(payload["functional_type"], team)

    for field, value in payload.items():
        setattr(military, field, value)
    military.sync_name_from_parts()

    try:
        db.session.flush()
        if team_supplied:
            _upsert_current_team(military, team, military.start_date)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return military


def activate_military(military: Military) -> Military:
    military.is_active = True
    db.session.commit()
    return military


def deactivate_military(military: Military) -> Military:
    military.is_active = False
    db.session.commit()
    return military


def nim_exists(nim: str, excluded_id: int | None = None) -> bool:
    statement = Military.query.filter(Military.nim == nim)
    if excluded_id is not None:
        statement = statement.filter(Military.id != excluded_id)
    return db.session.query(statement.exists()).scalar()


def _raise_for_duplicate_nim(nim: str, excluded_id: int | None = None) -> None:
    if nim_exists(nim, excluded_id=excluded_id):
        raise MilitaryServiceError({"nim": "Já existe um militar com este NIM."})


def _raise_for_invalid_functional_type_change(
    military: Military,
    new_functional_type: str,
) -> None:
    if (
        military.functional_type == "PATRULHEIRO"
        and new_functional_type != "PATRULHEIRO"
    ):
        from app.services.membership_service import get_current_membership

        if get_current_membership(military.id):
            raise MilitaryServiceError(
                {
                    "functional_type": (
                        "Nao e possivel alterar o tipo funcional enquanto existir "
                        "uma pertença atual a equipa."
                    )
                }
            )


def _get_valid_team(team_id: int | None) -> Team | None:
    team = db.session.get(Team, team_id) if team_id else None
    if team is None or not team.is_active:
        raise MilitaryServiceError({"team_id": "Selecione uma equipa operacional válida."})
    return team


def _raise_for_missing_or_invalid_team(functional_type: str, team: Team | None) -> None:
    if functional_type == FunctionalType.PATRULHEIRO.value and team is None:
        raise MilitaryServiceError({"team_id": "Patrulheiro exige equipa operacional A-E."})
    if functional_type != FunctionalType.PATRULHEIRO.value and team is not None:
        raise MilitaryServiceError({"team_id": "Apenas Patrulheiro pode ter equipa operacional A-E."})


def _upsert_current_team(military: Military, team: Team | None, start_date) -> None:
    if military.functional_type != FunctionalType.PATRULHEIRO.value or team is None:
        return

    current = military.current_team_membership
    if current and current.team_id == team.id:
        return
    if current and current.start_date >= start_date:
        current.team_id = team.id
        current.start_date = start_date
        current.reason = "Atualização de dados do militar."
        return
    if current:
        from datetime import timedelta

        current.end_date = start_date - timedelta(days=1)

    db.session.add(
        MilitaryTeamHistory(
            military_id=military.id,
            team_id=team.id,
            start_date=start_date,
            reason="Dados iniciais do militar.",
        )
    )
