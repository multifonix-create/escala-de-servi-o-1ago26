from sqlalchemy import func, or_

from app.extensions import db
from app.models import Military


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
            or_(Military.name.ilike(search), Military.nim.ilike(search))
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
    _raise_for_duplicate_nim(data["nim"])
    military = Military(**data)
    db.session.add(military)
    db.session.commit()
    return military


def update_military(military: Military, data: dict) -> Military:
    _raise_for_duplicate_nim(data["nim"], excluded_id=military.id)
    _raise_for_invalid_functional_type_change(military, data["functional_type"])

    for field, value in data.items():
        setattr(military, field, value)

    db.session.commit()
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
