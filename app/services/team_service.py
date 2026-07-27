from sqlalchemy import func

from app.extensions import db
from app.models import OFFICIAL_TEAM_CODES, MilitaryTeamHistory, Team


class TeamServiceError(Exception):
    def __init__(self, errors: dict[str, str]):
        super().__init__("Dados de equipa invalidos.")
        self.errors = errors


def list_teams() -> list[Team]:
    return Team.query.order_by(Team.code.asc()).all()


def get_team_or_404(team_id: int) -> Team:
    return db.get_or_404(Team, team_id)


def get_team(team_id: int) -> Team | None:
    return db.session.get(Team, team_id)


def get_team_by_code(code: str) -> Team | None:
    return Team.query.filter(Team.code == code).one_or_none()


def count_current_members(team_id: int) -> int:
    return (
        db.session.scalar(
            db.select(func.count(MilitaryTeamHistory.id)).where(
                MilitaryTeamHistory.team_id == team_id,
                MilitaryTeamHistory.end_date.is_(None),
            )
        )
        or 0
    )


def validate_official_teams() -> None:
    codes = [team.code for team in list_teams()]
    if codes != list(OFFICIAL_TEAM_CODES):
        raise TeamServiceError({"teams": "As equipas oficiais A-E nao estao completas."})
