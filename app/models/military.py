from datetime import UTC, datetime
from enum import StrEnum

from app.extensions import db


class FunctionalType(StrEnum):
    PATRULHEIRO = "PATRULHEIRO"
    SEC = "SEC"
    SI = "SI"
    CMD = "CMD"


FUNCTIONAL_TYPE_LABELS = {
    FunctionalType.CMD.value: "Comandante",
    FunctionalType.SEC.value: "Secretaria",
    FunctionalType.SI.value: "Serviço de Inquérito",
    FunctionalType.PATRULHEIRO.value: "Patrulheiro",
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def build_full_name(first_name: str | None, last_name: str | None, fallback: str = "") -> str:
    parts = [part.strip() for part in (first_name or "", last_name or "") if part and part.strip()]
    return " ".join(parts) or fallback.strip()


class Military(db.Model):
    __tablename__ = "militaries"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(180), nullable=False)
    first_name = db.Column(db.String(90), nullable=True, index=True)
    last_name = db.Column(db.String(120), nullable=True, index=True)
    nim = db.Column(db.String(30), nullable=False, unique=True, index=True)
    phone_number = db.Column(db.String(20), nullable=True)
    functional_type = db.Column(db.String(30), nullable=False, index=True)
    is_paid_service_volunteer = db.Column(db.Boolean, nullable=False, default=False)
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
    def full_name(self) -> str:
        return build_full_name(self.first_name, self.last_name, self.name)

    @property
    def functional_type_label(self) -> str:
        return FUNCTIONAL_TYPE_LABELS.get(self.functional_type, self.functional_type)

    @property
    def paid_service_volunteer_label(self) -> str:
        return "Sim" if self.is_paid_service_volunteer else "Não"

    def sync_name_from_parts(self) -> None:
        self.name = self.full_name

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
