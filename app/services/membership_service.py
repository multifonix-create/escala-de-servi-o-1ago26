from datetime import timedelta

from sqlalchemy import or_

from app.extensions import db
from app.models import FunctionalType, Military, MilitaryTeamHistory, Team


class MembershipServiceError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__("Dados de pertença a equipa invalidos.")
        self.errors = errors


def list_memberships_for_military(military_id: int) -> list[MilitaryTeamHistory]:
    return (
        MilitaryTeamHistory.query.filter(MilitaryTeamHistory.military_id == military_id)
        .order_by(MilitaryTeamHistory.start_date.desc(), MilitaryTeamHistory.id.desc())
        .all()
    )


def list_current_members_for_team(team_id: int) -> list[MilitaryTeamHistory]:
    return (
        MilitaryTeamHistory.query.filter(
            MilitaryTeamHistory.team_id == team_id,
            MilitaryTeamHistory.end_date.is_(None),
        )
        .join(Military)
        .order_by(Military.name.asc(), Military.nim.asc())
        .all()
    )


def list_history_for_team(team_id: int) -> list[MilitaryTeamHistory]:
    return (
        MilitaryTeamHistory.query.filter(MilitaryTeamHistory.team_id == team_id)
        .join(Military)
        .order_by(MilitaryTeamHistory.start_date.desc(), Military.name.asc())
        .all()
    )


def get_membership_or_404(membership_id: int) -> MilitaryTeamHistory:
    return db.get_or_404(MilitaryTeamHistory, membership_id)


def get_current_membership(military_id: int) -> MilitaryTeamHistory | None:
    return (
        MilitaryTeamHistory.query.filter(
            MilitaryTeamHistory.military_id == military_id,
            MilitaryTeamHistory.end_date.is_(None),
        )
        .order_by(MilitaryTeamHistory.start_date.desc())
        .one_or_none()
    )


def get_team_for_military_on_date(military_id: int, reference_date):
    membership = (
        MilitaryTeamHistory.query.filter(
            MilitaryTeamHistory.military_id == military_id,
            MilitaryTeamHistory.start_date <= reference_date,
            or_(
                MilitaryTeamHistory.end_date.is_(None),
                MilitaryTeamHistory.end_date >= reference_date,
            ),
        )
        .order_by(MilitaryTeamHistory.start_date.desc())
        .first()
    )
    return membership.team if membership else None


def assign_military_to_team(
    military: Military,
    team: Team,
    start_date,
    reason: str | None = None,
) -> MilitaryTeamHistory:
    _validate_military_can_have_team(military)
    _validate_team(team)
    _validate_date_within_military_record(military, start_date, None)

    if get_current_membership(military.id):
        raise MembershipServiceError(
            {"team_id": "O militar ja possui uma equipa atual. Use a mudanca de equipa."}
        )
    if has_overlapping_membership(military.id, start_date, None):
        raise MembershipServiceError(
            {"start_date": "O periodo indicado sobrepoe-se ao historico existente."}
        )

    membership = MilitaryTeamHistory(
        military_id=military.id,
        team_id=team.id,
        start_date=start_date,
        reason=reason,
    )
    try:
        db.session.add(membership)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return membership


def change_military_team(
    military: Military,
    new_team: Team,
    effective_date,
    reason: str | None = None,
) -> MilitaryTeamHistory:
    _validate_military_can_have_team(military)
    _validate_team(new_team)
    _validate_date_within_military_record(military, effective_date, None)

    current = get_current_membership(military.id)
    if current is None:
        raise MembershipServiceError(
            {"team_id": "O militar nao possui equipa atual para alterar."}
        )
    if current.team_id == new_team.id:
        raise MembershipServiceError(
            {"team_id": "A nova equipa deve ser diferente da equipa atual."}
        )
    if effective_date <= current.start_date:
        raise MembershipServiceError(
            {
                "start_date": "A data da mudanca deve ser posterior ao inicio da pertença atual."
            }
        )

    previous_end_date = effective_date - timedelta(days=1)
    if has_overlapping_membership(
        military.id,
        effective_date,
        None,
        excluded_id=current.id,
    ):
        raise MembershipServiceError(
            {"start_date": "O periodo indicado sobrepoe-se ao historico existente."}
        )

    new_membership = MilitaryTeamHistory(
        military_id=military.id,
        team_id=new_team.id,
        start_date=effective_date,
        reason=reason,
    )
    try:
        current.end_date = previous_end_date
        db.session.add(new_membership)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return new_membership


def update_membership(
    membership: MilitaryTeamHistory,
    start_date,
    end_date,
    reason: str | None = None,
) -> MilitaryTeamHistory:
    _validate_date_within_military_record(membership.military, start_date, end_date)
    if has_overlapping_membership(
        membership.military_id,
        start_date,
        end_date,
        excluded_id=membership.id,
    ):
        raise MembershipServiceError(
            {"start_date": "O periodo indicado sobrepoe-se ao historico existente."}
        )

    try:
        membership.start_date = start_date
        membership.end_date = end_date
        membership.reason = reason
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return membership


def has_overlapping_membership(
    military_id: int,
    start_date,
    end_date,
    excluded_id: int | None = None,
) -> bool:
    statement = MilitaryTeamHistory.query.filter(
        MilitaryTeamHistory.military_id == military_id,
        MilitaryTeamHistory.start_date <= (end_date or start_date.max),
        or_(
            MilitaryTeamHistory.end_date.is_(None),
            MilitaryTeamHistory.end_date >= start_date,
        ),
    )
    if excluded_id is not None:
        statement = statement.filter(MilitaryTeamHistory.id != excluded_id)
    return db.session.query(statement.exists()).scalar()


def _validate_military_can_have_team(military: Military) -> None:
    if military.functional_type != FunctionalType.PATRULHEIRO.value:
        raise MembershipServiceError(
            {"military": "Apenas militares PATRULHEIRO podem pertencer a equipas."}
        )


def _validate_team(team: Team) -> None:
    if team is None or not team.is_active:
        raise MembershipServiceError({"team_id": "Selecione uma equipa ativa valida."})


def _validate_date_within_military_record(military: Military, start_date, end_date) -> None:
    if start_date < military.start_date:
        raise MembershipServiceError(
            {"start_date": "A data de inicio nao pode ser anterior ao inicio do militar."}
        )
    if military.end_date and start_date > military.end_date:
        raise MembershipServiceError(
            {"start_date": "A data de inicio nao pode ser posterior ao fim do militar."}
        )
    if end_date and military.end_date and end_date > military.end_date:
        raise MembershipServiceError(
            {"end_date": "A data de fim nao pode ser posterior ao fim do militar."}
        )
