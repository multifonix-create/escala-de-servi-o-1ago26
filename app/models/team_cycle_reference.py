from app.extensions import db
from app.models.military import utc_now


class TeamCycleReference(db.Model):
    __tablename__ = "team_cycle_references"
    __table_args__ = (
        db.CheckConstraint(
            "reference_phase between 1 and 6",
            name="ck_team_cycle_references_phase",
        ),
        db.CheckConstraint(
            "valid_until is null or valid_until >= valid_from",
            name="ck_team_cycle_references_valid_period",
        ),
        db.UniqueConstraint(
            "team_id",
            "valid_from",
            name="uq_team_cycle_references_team_valid_from",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(
        db.Integer,
        db.ForeignKey("teams.id"),
        nullable=False,
        index=True,
    )
    reference_date = db.Column(db.Date, nullable=False, index=True)
    reference_phase = db.Column(db.Integer, nullable=False)
    valid_from = db.Column(db.Date, nullable=False, index=True)
    valid_until = db.Column(db.Date, nullable=True, index=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        onupdate=utc_now,
    )

    team = db.relationship("Team", back_populates="cycle_references")

    def is_valid_on(self, reference_date) -> bool:
        return self.valid_from <= reference_date and (
            self.valid_until is None or reference_date <= self.valid_until
        )
