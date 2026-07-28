from datetime import UTC, datetime
from enum import StrEnum

from app.extensions import db


class FunctionalType(StrEnum):
    PATRULHEIRO = "PATRULHEIRO"
    SEC = "SEC"
    SI = "SI"
    CMD = "CMD"


def utc_now() -> datetime:
    return datetime.now(UTC)


class Military(db.Model):
    __tablename__ = "militaries"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    nim = db.Column(db.String(30), nullable=False, unique=True, index=True)
    functional_type = db.Column(db.String(30), nullable=False, index=True)
    is_active = db.Column(db.Boolean, nullable=False, default=True, index=True)
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )
    team_memberships = db.relationship(
        "MilitaryTeamHistory",
        back_populates="military",
        order_by="MilitaryTeamHistory.start_date.asc()",
    )
    restrictions = db.relationship(
        "MilitaryRestriction",
        back_populates="military",
        order_by="MilitaryRestriction.start_date.desc()",
    )
    unavailabilities = db.relationship(
        "Unavailability",
        back_populates="military",
        order_by="Unavailability.start_date.desc()",
    )

    def has_inactive_date_warning(self, today=None) -> bool:
        reference_date = today or utc_now().date()
        return self.is_active and self.end_date is not None and self.end_date < reference_date

    @property
    def current_team_membership(self):
        memberships = sorted(
            self.team_memberships,
            key=lambda membership: membership.start_date,
            reverse=True,
        )
        return next(
            (membership for membership in memberships if membership.end_date is None),
            None,
        )

    @property
    def current_team(self):
        membership = self.current_team_membership
        return membership.team if membership else None

    @property
    def active_restrictions(self):
        return [restriction for restriction in self.restrictions if restriction.is_active]

    @property
    def active_unavailabilities(self):
        return [
            unavailability
            for unavailability in self.unavailabilities
            if unavailability.is_active and unavailability.status != "CANCELLED"
        ]
