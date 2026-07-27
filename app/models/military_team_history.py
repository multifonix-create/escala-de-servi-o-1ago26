from app.extensions import db
from app.models.military import utc_now


class MilitaryTeamHistory(db.Model):
    __tablename__ = "military_team_history"

    id = db.Column(db.Integer, primary_key=True)
    military_id = db.Column(
        db.Integer,
        db.ForeignKey("militaries.id"),
        nullable=False,
        index=True,
    )
    team_id = db.Column(
        db.Integer,
        db.ForeignKey("teams.id"),
        nullable=False,
        index=True,
    )
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=True, index=True)
    reason = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    military = db.relationship("Military", back_populates="team_memberships")
    team = db.relationship("Team", back_populates="memberships")

    def contains_date(self, reference_date) -> bool:
        return self.start_date <= reference_date and (
            self.end_date is None or reference_date <= self.end_date
        )
