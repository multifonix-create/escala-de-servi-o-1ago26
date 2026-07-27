from enum import StrEnum

from app.extensions import db
from app.models.military import utc_now


class TeamCode(StrEnum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"


OFFICIAL_TEAM_CODES = tuple(item.value for item in TeamCode)


class Team(db.Model):
    __tablename__ = "teams"
    __table_args__ = (
        db.CheckConstraint(
            "code in ('A', 'B', 'C', 'D', 'E')",
            name="ck_teams_official_code",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(1), nullable=False, unique=True, index=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    memberships = db.relationship(
        "MilitaryTeamHistory",
        back_populates="team",
        order_by="MilitaryTeamHistory.start_date.asc()",
    )
    cycle_references = db.relationship(
        "TeamCycleReference",
        back_populates="team",
        order_by="TeamCycleReference.valid_from.asc()",
    )

    @property
    def current_memberships(self):
        return [
            membership
            for membership in self.memberships
            if membership.end_date is None
        ]
