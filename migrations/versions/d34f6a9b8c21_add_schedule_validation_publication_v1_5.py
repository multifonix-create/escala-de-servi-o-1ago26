"""add schedule validation publication v1.5

Revision ID: d34f6a9b8c21
Revises: 621f28c3f5b5
Create Date: 2026-07-28 16:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d34f6a9b8c21"
down_revision = "621f28c3f5b5"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("schedule_versions") as batch_op:
        batch_op.add_column(sa.Column("content_revision", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("validated_revision", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("validated_diagnostic_run_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("state_notes", sa.Text(), nullable=True))
        batch_op.create_index("ix_schedule_versions_validated_diagnostic_run_id", ["validated_diagnostic_run_id"])
        batch_op.create_foreign_key(
            "fk_schedule_versions_validated_diagnostic_run_id",
            "diagnostic_runs",
            ["validated_diagnostic_run_id"],
            ["id"],
        )

    with op.batch_alter_table("schedule_months") as batch_op:
        batch_op.add_column(sa.Column("published_version_id", sa.Integer(), nullable=True))
        batch_op.create_index("ix_schedule_months_published_version_id", ["published_version_id"])
        batch_op.create_foreign_key(
            "fk_schedule_months_published_version_id",
            "schedule_versions",
            ["published_version_id"],
            ["id"],
        )

    op.create_table(
        "schedule_version_state_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("schedule_version_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("previous_state", sa.String(length=30), nullable=True),
        sa.Column("new_state", sa.String(length=30), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("diagnostic_run_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "event_type in ('VALIDATED', 'VALIDATION_REVOKED', 'PUBLISHED', 'UNPUBLISHED', 'CLOSED', 'REOPENED_AS_NEW_VERSION')",
            name="ck_schedule_version_state_events_type",
        ),
        sa.CheckConstraint(
            "previous_state is null or previous_state in ('NOT_GENERATED', 'DRAFT', 'VALIDATED', 'PUBLISHED', 'CLOSED')",
            name="ck_schedule_version_state_events_previous_state",
        ),
        sa.CheckConstraint(
            "new_state is null or new_state in ('NOT_GENERATED', 'DRAFT', 'VALIDATED', 'PUBLISHED', 'CLOSED')",
            name="ck_schedule_version_state_events_new_state",
        ),
        sa.ForeignKeyConstraint(["diagnostic_run_id"], ["diagnostic_runs.id"]),
        sa.ForeignKeyConstraint(["schedule_version_id"], ["schedule_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_schedule_version_state_events_diagnostic_run_id",
        "schedule_version_state_events",
        ["diagnostic_run_id"],
    )
    op.create_index(
        "ix_schedule_version_state_events_event_type",
        "schedule_version_state_events",
        ["event_type"],
    )
    op.create_index(
        "ix_schedule_version_state_events_schedule_version_id",
        "schedule_version_state_events",
        ["schedule_version_id"],
    )


def downgrade():
    op.drop_index("ix_schedule_version_state_events_schedule_version_id", table_name="schedule_version_state_events")
    op.drop_index("ix_schedule_version_state_events_event_type", table_name="schedule_version_state_events")
    op.drop_index("ix_schedule_version_state_events_diagnostic_run_id", table_name="schedule_version_state_events")
    op.drop_table("schedule_version_state_events")

    with op.batch_alter_table("schedule_months") as batch_op:
        batch_op.drop_constraint("fk_schedule_months_published_version_id", type_="foreignkey")
        batch_op.drop_index("ix_schedule_months_published_version_id")
        batch_op.drop_column("published_version_id")

    with op.batch_alter_table("schedule_versions") as batch_op:
        batch_op.drop_constraint("fk_schedule_versions_validated_diagnostic_run_id", type_="foreignkey")
        batch_op.drop_index("ix_schedule_versions_validated_diagnostic_run_id")
        batch_op.drop_column("state_notes")
        batch_op.drop_column("closed_at")
        batch_op.drop_column("published_at")
        batch_op.drop_column("validated_diagnostic_run_id")
        batch_op.drop_column("validated_at")
        batch_op.drop_column("validated_revision")
        batch_op.drop_column("content_revision")
