"""add fc fr compensations v1.6

Revision ID: 9a4e2b7c1d60
Revises: d34f6a9b8c21
Create Date: 2026-07-28 17:55:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "9a4e2b7c1d60"
down_revision = "d34f6a9b8c21"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "compensatory_leave_credits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("military_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("source_assignment_id", sa.Integer(), nullable=True),
        sa.Column("source_schedule_version_id", sa.Integer(), nullable=True),
        sa.Column("source_service_date", sa.Date(), nullable=False),
        sa.Column("source_service_code", sa.String(length=30), nullable=True),
        sa.Column("unit_number", sa.Integer(), nullable=False),
        sa.Column("units_from_source", sa.Integer(), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("acquired_date", sa.Date(), nullable=False),
        sa.Column("expires_on", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("expiry_protected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("commander_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source_type in ('RONDA', 'CONDUTOR_RONDANTE', 'COMMANDER_DISCRETION')", name="ck_compensatory_leave_credits_source_type"),
        sa.CheckConstraint("status in ('PENDING', 'SCHEDULED', 'RESCHEDULED', 'USED', 'CANCELLED', 'EXPIRED')", name="ck_compensatory_leave_credits_status"),
        sa.CheckConstraint("minutes = 480", name="ck_compensatory_leave_credits_minutes"),
        sa.CheckConstraint("unit_number >= 1", name="ck_compensatory_leave_credits_unit_number"),
        sa.CheckConstraint("units_from_source >= 1", name="ck_compensatory_leave_credits_units_from_source"),
        sa.ForeignKeyConstraint(["military_id"], ["militaries.id"]),
        sa.ForeignKeyConstraint(["source_assignment_id"], ["assignments.id"]),
        sa.ForeignKeyConstraint(["source_schedule_version_id"], ["schedule_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("military_id", "source_type", "source_service_date", "source_service_code", "unit_number", name="uq_compensatory_leave_credits_source_unit"),
    )
    for column in (
        "military_id",
        "source_type",
        "source_assignment_id",
        "source_schedule_version_id",
        "source_service_date",
        "source_service_code",
        "acquired_date",
        "expires_on",
        "status",
        "scheduled_date",
        "effective_date",
    ):
        op.create_index(f"ix_compensatory_leave_credits_{column}", "compensatory_leave_credits", [column])

    op.create_table(
        "compensatory_leave_credit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("credit_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=True),
        sa.Column("previous_scheduled_date", sa.Date(), nullable=True),
        sa.Column("new_scheduled_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("is_automatic", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("event_type in ('CREATED', 'SCHEDULED', 'RESCHEDULED', 'SCHEDULE_CANCELLED', 'USED', 'AUTO_USED', 'CANCELLED', 'EXPIRED', 'NOTES_UPDATED')", name="ck_compensatory_leave_credit_events_type"),
        sa.CheckConstraint("previous_status is null or previous_status in ('PENDING', 'SCHEDULED', 'RESCHEDULED', 'USED', 'CANCELLED', 'EXPIRED')", name="ck_compensatory_leave_credit_events_previous_status"),
        sa.CheckConstraint("new_status is null or new_status in ('PENDING', 'SCHEDULED', 'RESCHEDULED', 'USED', 'CANCELLED', 'EXPIRED')", name="ck_compensatory_leave_credit_events_new_status"),
        sa.ForeignKeyConstraint(["credit_id"], ["compensatory_leave_credits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_compensatory_leave_credit_events_credit_id", "compensatory_leave_credit_events", ["credit_id"])
    op.create_index("ix_compensatory_leave_credit_events_event_type", "compensatory_leave_credit_events", ["event_type"])
    op.create_index("ix_compensatory_leave_credit_events_is_automatic", "compensatory_leave_credit_events", ["is_automatic"])

    op.create_table(
        "rescheduled_rest_credits",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("military_id", sa.Integer(), nullable=False),
        sa.Column("source_assignment_id", sa.Integer(), nullable=True),
        sa.Column("source_schedule_version_id", sa.Integer(), nullable=True),
        sa.Column("original_rest_date", sa.Date(), nullable=False),
        sa.Column("original_rest_type", sa.String(length=2), nullable=False),
        sa.Column("source_service_code", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("original_rest_type in ('DS', 'DC')", name="ck_rescheduled_rest_credits_rest_type"),
        sa.CheckConstraint("source_service_code in ('AT1', 'AT2', 'AT3', 'PO1', 'PO2', 'PO3', 'PT')", name="ck_rescheduled_rest_credits_source_service_code"),
        sa.CheckConstraint("status in ('PENDING', 'SCHEDULED', 'RESCHEDULED', 'USED', 'CANCELLED')", name="ck_rescheduled_rest_credits_status"),
        sa.ForeignKeyConstraint(["military_id"], ["militaries.id"]),
        sa.ForeignKeyConstraint(["source_assignment_id"], ["assignments.id"]),
        sa.ForeignKeyConstraint(["source_schedule_version_id"], ["schedule_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("military_id", "original_rest_date", "original_rest_type", name="uq_rescheduled_rest_credits_origin_day"),
    )
    for column in (
        "military_id",
        "source_assignment_id",
        "source_schedule_version_id",
        "original_rest_date",
        "original_rest_type",
        "source_service_code",
        "status",
        "scheduled_date",
        "effective_date",
    ):
        op.create_index(f"ix_rescheduled_rest_credits_{column}", "rescheduled_rest_credits", [column])

    op.create_table(
        "rescheduled_rest_credit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("credit_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=True),
        sa.Column("previous_scheduled_date", sa.Date(), nullable=True),
        sa.Column("new_scheduled_date", sa.Date(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("is_automatic", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("event_type in ('CREATED', 'SCHEDULED', 'RESCHEDULED', 'SCHEDULE_CANCELLED', 'USED', 'CANCELLED', 'NOTES_UPDATED')", name="ck_rescheduled_rest_credit_events_type"),
        sa.CheckConstraint("previous_status is null or previous_status in ('PENDING', 'SCHEDULED', 'RESCHEDULED', 'USED', 'CANCELLED')", name="ck_rescheduled_rest_credit_events_previous_status"),
        sa.CheckConstraint("new_status is null or new_status in ('PENDING', 'SCHEDULED', 'RESCHEDULED', 'USED', 'CANCELLED')", name="ck_rescheduled_rest_credit_events_new_status"),
        sa.ForeignKeyConstraint(["credit_id"], ["rescheduled_rest_credits.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rescheduled_rest_credit_events_credit_id", "rescheduled_rest_credit_events", ["credit_id"])
    op.create_index("ix_rescheduled_rest_credit_events_event_type", "rescheduled_rest_credit_events", ["event_type"])
    op.create_index("ix_rescheduled_rest_credit_events_is_automatic", "rescheduled_rest_credit_events", ["is_automatic"])

    with op.batch_alter_table("assignments") as batch_op:
        batch_op.drop_constraint("ck_assignments_code", type_="check")
        batch_op.add_column(sa.Column("compensatory_leave_credit_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("rescheduled_rest_credit_id", sa.Integer(), nullable=True))
        batch_op.create_check_constraint(
            "ck_assignments_code",
            "code is null or code in ('AT1', 'AT2', 'AT3', 'PO1', 'PO2', 'PO3', 'PT', 'P', 'R', 'CR', 'FC', 'FF', 'FR', 'DS', 'DC', 'LF', 'LP', 'BM', 'LC', 'LN', 'DIL', 'TRIB', 'INQ', 'DCP', 'D24', 'FORMACAO', 'TIRO', 'OUTRA')",
        )
        batch_op.create_check_constraint(
            "ck_assignments_single_leave_link",
            "(case when holiday_leave_credit_id is not null then 1 else 0 end + case when compensatory_leave_credit_id is not null then 1 else 0 end + case when rescheduled_rest_credit_id is not null then 1 else 0 end) <= 1",
        )
        batch_op.create_check_constraint(
            "ck_assignments_leave_code_link",
            "(code != 'FF' or holiday_leave_credit_id is not null) and (code != 'FC' or compensatory_leave_credit_id is not null) and (code != 'FR' or rescheduled_rest_credit_id is not null) and (code in ('FF', 'FC', 'FR') or (holiday_leave_credit_id is null and compensatory_leave_credit_id is null and rescheduled_rest_credit_id is null))",
        )
        batch_op.create_index("ix_assignments_compensatory_leave_credit_id", ["compensatory_leave_credit_id"])
        batch_op.create_index("ix_assignments_rescheduled_rest_credit_id", ["rescheduled_rest_credit_id"])
        batch_op.create_foreign_key(
            "fk_assignments_compensatory_leave_credit_id",
            "compensatory_leave_credits",
            ["compensatory_leave_credit_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_assignments_rescheduled_rest_credit_id",
            "rescheduled_rest_credits",
            ["rescheduled_rest_credit_id"],
            ["id"],
        )


def downgrade():
    with op.batch_alter_table("assignments") as batch_op:
        batch_op.drop_constraint("fk_assignments_rescheduled_rest_credit_id", type_="foreignkey")
        batch_op.drop_constraint("fk_assignments_compensatory_leave_credit_id", type_="foreignkey")
        batch_op.drop_index("ix_assignments_rescheduled_rest_credit_id")
        batch_op.drop_index("ix_assignments_compensatory_leave_credit_id")
        batch_op.drop_constraint("ck_assignments_leave_code_link", type_="check")
        batch_op.drop_constraint("ck_assignments_single_leave_link", type_="check")
        batch_op.drop_constraint("ck_assignments_code", type_="check")
        batch_op.create_check_constraint(
            "ck_assignments_code",
            "code is null or code in ('AT1', 'AT2', 'AT3', 'PO1', 'PO2', 'PO3', 'PT', 'P', 'R', 'CR', 'FC', 'FF', 'DS', 'DC', 'LF', 'LP', 'BM', 'LC', 'LN', 'DIL', 'TRIB', 'INQ', 'DCP', 'D24', 'FORMACAO', 'TIRO', 'OUTRA')",
        )
        batch_op.drop_column("rescheduled_rest_credit_id")
        batch_op.drop_column("compensatory_leave_credit_id")

    op.drop_index("ix_rescheduled_rest_credit_events_is_automatic", table_name="rescheduled_rest_credit_events")
    op.drop_index("ix_rescheduled_rest_credit_events_event_type", table_name="rescheduled_rest_credit_events")
    op.drop_index("ix_rescheduled_rest_credit_events_credit_id", table_name="rescheduled_rest_credit_events")
    op.drop_table("rescheduled_rest_credit_events")

    for column in (
        "effective_date",
        "scheduled_date",
        "status",
        "source_service_code",
        "original_rest_type",
        "original_rest_date",
        "source_schedule_version_id",
        "source_assignment_id",
        "military_id",
    ):
        op.drop_index(f"ix_rescheduled_rest_credits_{column}", table_name="rescheduled_rest_credits")
    op.drop_table("rescheduled_rest_credits")

    op.drop_index("ix_compensatory_leave_credit_events_is_automatic", table_name="compensatory_leave_credit_events")
    op.drop_index("ix_compensatory_leave_credit_events_event_type", table_name="compensatory_leave_credit_events")
    op.drop_index("ix_compensatory_leave_credit_events_credit_id", table_name="compensatory_leave_credit_events")
    op.drop_table("compensatory_leave_credit_events")

    for column in (
        "effective_date",
        "scheduled_date",
        "status",
        "expires_on",
        "acquired_date",
        "source_service_code",
        "source_service_date",
        "source_schedule_version_id",
        "source_assignment_id",
        "source_type",
        "military_id",
    ):
        op.drop_index(f"ix_compensatory_leave_credits_{column}", table_name="compensatory_leave_credits")
    op.drop_table("compensatory_leave_credits")
