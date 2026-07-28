from datetime import date

from sqlalchemy import or_

from app.extensions import db
from app.models import Military, MilitaryRestriction, WEEKDAY_FIELDS


class RestrictionServiceError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__("Dados de restrição inválidos.")
        self.errors = errors


def list_restrictions(
    military_id: int | None = None,
    restriction_type: str | None = None,
    status: str | None = None,
) -> list[MilitaryRestriction]:
    statement = MilitaryRestriction.query.join(Military)
    if military_id is not None:
        statement = statement.filter(MilitaryRestriction.military_id == military_id)
    if restriction_type:
        statement = statement.filter(MilitaryRestriction.restriction_type == restriction_type)
    if status == "active":
        statement = statement.filter(MilitaryRestriction.is_active.is_(True))
    elif status == "inactive":
        statement = statement.filter(MilitaryRestriction.is_active.is_(False))
    return (
        statement.order_by(
            Military.name.asc(),
            MilitaryRestriction.start_date.desc(),
            MilitaryRestriction.id.desc(),
        )
        .all()
    )


def list_restrictions_for_military(military_id: int) -> list[MilitaryRestriction]:
    return list_restrictions(military_id=military_id)


def count_active_restrictions_for_military(military_id: int) -> int:
    return (
        db.session.query(MilitaryRestriction)
        .filter(
            MilitaryRestriction.military_id == military_id,
            MilitaryRestriction.is_active.is_(True),
        )
        .count()
    )


def get_restriction_or_404(restriction_id: int) -> MilitaryRestriction:
    return db.get_or_404(MilitaryRestriction, restriction_id)


def get_active_restrictions_for_military_on_date(
    military_id: int,
    reference_date: date,
) -> list[MilitaryRestriction]:
    return (
        MilitaryRestriction.query.filter(
            MilitaryRestriction.military_id == military_id,
            MilitaryRestriction.is_active.is_(True),
            MilitaryRestriction.start_date <= reference_date,
            or_(
                MilitaryRestriction.end_date.is_(None),
                MilitaryRestriction.end_date >= reference_date,
            ),
        )
        .order_by(MilitaryRestriction.restriction_type.asc(), MilitaryRestriction.id.asc())
        .all()
    )


def create_restriction(military: Military, data: dict) -> MilitaryRestriction:
    _raise_for_duplicate(military.id, data)
    restriction = MilitaryRestriction(military_id=military.id, **data)
    try:
        db.session.add(restriction)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return restriction


def update_restriction(restriction: MilitaryRestriction, data: dict) -> MilitaryRestriction:
    _raise_for_duplicate(restriction.military_id, data, excluded_id=restriction.id)
    try:
        for field, value in data.items():
            setattr(restriction, field, value)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return restriction


def activate_restriction(restriction: MilitaryRestriction) -> MilitaryRestriction:
    restriction.is_active = True
    db.session.commit()
    return restriction


def deactivate_restriction(restriction: MilitaryRestriction) -> MilitaryRestriction:
    restriction.is_active = False
    db.session.commit()
    return restriction


def weekdays_summary(restriction: MilitaryRestriction) -> str:
    selected = restriction.selected_weekdays
    if not selected:
        return "Todos os dias"
    names = {
        "monday": "segunda-feira",
        "tuesday": "terça-feira",
        "wednesday": "quarta-feira",
        "thursday": "quinta-feira",
        "friday": "sexta-feira",
        "saturday": "sábado",
        "sunday": "domingo",
    }
    return ", ".join(names[field] for field in selected)


def _raise_for_duplicate(
    military_id: int,
    data: dict,
    excluded_id: int | None = None,
) -> None:
    statement = MilitaryRestriction.query.filter(
        MilitaryRestriction.military_id == military_id,
        MilitaryRestriction.restriction_type == data["restriction_type"],
        MilitaryRestriction.start_date == data["start_date"],
        MilitaryRestriction.end_date.is_(data["end_date"])
        if data["end_date"] is None
        else MilitaryRestriction.end_date == data["end_date"],
        MilitaryRestriction.start_time.is_(data["start_time"])
        if data["start_time"] is None
        else MilitaryRestriction.start_time == data["start_time"],
        MilitaryRestriction.end_time.is_(data["end_time"])
        if data["end_time"] is None
        else MilitaryRestriction.end_time == data["end_time"],
    )
    for field in WEEKDAY_FIELDS:
        statement = statement.filter(getattr(MilitaryRestriction, field).is_(data[field]))
    if excluded_id is not None:
        statement = statement.filter(MilitaryRestriction.id != excluded_id)
    if db.session.query(statement.exists()).scalar():
        raise RestrictionServiceError(
            {"duplicate": "Já existe uma restrição igual para este militar."}
        )
