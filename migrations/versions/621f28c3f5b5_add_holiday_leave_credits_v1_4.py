"""add holiday leave credits v1.4

Revision ID: 621f28c3f5b5
Revises: adaa03cbb54b
Create Date: 2026-07-28 16:11:57.043791

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '621f28c3f5b5'
down_revision = 'adaa03cbb54b'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('holidays',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('holiday_date', sa.Date(), nullable=False),
    sa.Column('name', sa.String(length=150), nullable=False),
    sa.Column('scope', sa.String(length=30), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("scope in ('NATIONAL', 'MUNICIPAL', 'LOCAL', 'INSTITUTIONAL')", name='ck_holidays_scope'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('holiday_date', 'scope', name='uq_holidays_date_scope')
    )
    with op.batch_alter_table('holidays', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_holidays_holiday_date'), ['holiday_date'], unique=False)
        batch_op.create_index(batch_op.f('ix_holidays_is_active'), ['is_active'], unique=False)
        batch_op.create_index(batch_op.f('ix_holidays_scope'), ['scope'], unique=False)

    op.create_table('holiday_leave_credits',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('military_id', sa.Integer(), nullable=False),
    sa.Column('holiday_id', sa.Integer(), nullable=False),
    sa.Column('source_assignment_id', sa.Integer(), nullable=False),
    sa.Column('source_schedule_version_id', sa.Integer(), nullable=False),
    sa.Column('source_generation_run_id', sa.Integer(), nullable=True),
    sa.Column('service_date', sa.Date(), nullable=False),
    sa.Column('service_code', sa.String(length=30), nullable=False),
    sa.Column('acquired_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.String(length=30), nullable=False),
    sa.Column('scheduled_date', sa.Date(), nullable=True),
    sa.Column('effective_date', sa.Date(), nullable=True),
    sa.Column('cancellation_reason', sa.Text(), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("service_code in ('AT1', 'AT2', 'AT3', 'PO1', 'PO2', 'PO3', 'PT')", name='ck_holiday_leave_credits_service_code'),
    sa.CheckConstraint("status in ('PENDING', 'SCHEDULED', 'USED', 'RESCHEDULED', 'CANCELLED')", name='ck_holiday_leave_credits_status'),
    sa.ForeignKeyConstraint(['holiday_id'], ['holidays.id'], ),
    sa.ForeignKeyConstraint(['military_id'], ['militaries.id'], ),
    sa.ForeignKeyConstraint(['source_assignment_id'], ['assignments.id'], ),
    sa.ForeignKeyConstraint(['source_generation_run_id'], ['generation_runs.id'], ),
    sa.ForeignKeyConstraint(['source_schedule_version_id'], ['schedule_versions.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_assignment_id', name='uq_holiday_leave_credits_source_assignment')
    )
    with op.batch_alter_table('holiday_leave_credits', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_holiday_leave_credits_effective_date'), ['effective_date'], unique=False)
        batch_op.create_index(batch_op.f('ix_holiday_leave_credits_holiday_id'), ['holiday_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_holiday_leave_credits_military_id'), ['military_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_holiday_leave_credits_scheduled_date'), ['scheduled_date'], unique=False)
        batch_op.create_index(batch_op.f('ix_holiday_leave_credits_service_code'), ['service_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_holiday_leave_credits_service_date'), ['service_date'], unique=False)
        batch_op.create_index(batch_op.f('ix_holiday_leave_credits_source_assignment_id'), ['source_assignment_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_holiday_leave_credits_source_generation_run_id'), ['source_generation_run_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_holiday_leave_credits_source_schedule_version_id'), ['source_schedule_version_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_holiday_leave_credits_status'), ['status'], unique=False)

    op.create_table('holiday_leave_credit_events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('credit_id', sa.Integer(), nullable=False),
    sa.Column('event_type', sa.String(length=40), nullable=False),
    sa.Column('previous_status', sa.String(length=30), nullable=True),
    sa.Column('new_status', sa.String(length=30), nullable=True),
    sa.Column('previous_scheduled_date', sa.Date(), nullable=True),
    sa.Column('new_scheduled_date', sa.Date(), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("event_type in ('CREATED', 'SCHEDULED', 'RESCHEDULED', 'SCHEDULE_CANCELLED', 'USED', 'CANCELLED', 'NOTES_UPDATED')", name='ck_holiday_leave_credit_events_type'),
    sa.CheckConstraint("new_status is null or new_status in ('PENDING', 'SCHEDULED', 'USED', 'RESCHEDULED', 'CANCELLED')", name='ck_holiday_leave_credit_events_new_status'),
    sa.CheckConstraint("previous_status is null or previous_status in ('PENDING', 'SCHEDULED', 'USED', 'RESCHEDULED', 'CANCELLED')", name='ck_holiday_leave_credit_events_previous_status'),
    sa.ForeignKeyConstraint(['credit_id'], ['holiday_leave_credits.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('holiday_leave_credit_events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_holiday_leave_credit_events_credit_id'), ['credit_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_holiday_leave_credit_events_event_type'), ['event_type'], unique=False)

    with op.batch_alter_table('assignments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('holiday_leave_credit_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_assignments_holiday_leave_credit_id'), ['holiday_leave_credit_id'], unique=False)
        batch_op.create_foreign_key('fk_assignments_holiday_leave_credit_id', 'holiday_leave_credits', ['holiday_leave_credit_id'], ['id'])


def downgrade():
    with op.batch_alter_table('assignments', schema=None) as batch_op:
        batch_op.drop_constraint('fk_assignments_holiday_leave_credit_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_assignments_holiday_leave_credit_id'))
        batch_op.drop_column('holiday_leave_credit_id')

    with op.batch_alter_table('holiday_leave_credit_events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_holiday_leave_credit_events_event_type'))
        batch_op.drop_index(batch_op.f('ix_holiday_leave_credit_events_credit_id'))

    op.drop_table('holiday_leave_credit_events')
    with op.batch_alter_table('holiday_leave_credits', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_holiday_leave_credits_status'))
        batch_op.drop_index(batch_op.f('ix_holiday_leave_credits_source_schedule_version_id'))
        batch_op.drop_index(batch_op.f('ix_holiday_leave_credits_source_generation_run_id'))
        batch_op.drop_index(batch_op.f('ix_holiday_leave_credits_source_assignment_id'))
        batch_op.drop_index(batch_op.f('ix_holiday_leave_credits_service_date'))
        batch_op.drop_index(batch_op.f('ix_holiday_leave_credits_service_code'))
        batch_op.drop_index(batch_op.f('ix_holiday_leave_credits_scheduled_date'))
        batch_op.drop_index(batch_op.f('ix_holiday_leave_credits_military_id'))
        batch_op.drop_index(batch_op.f('ix_holiday_leave_credits_holiday_id'))
        batch_op.drop_index(batch_op.f('ix_holiday_leave_credits_effective_date'))

    op.drop_table('holiday_leave_credits')
    with op.batch_alter_table('holidays', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_holidays_scope'))
        batch_op.drop_index(batch_op.f('ix_holidays_is_active'))
        batch_op.drop_index(batch_op.f('ix_holidays_holiday_date'))

    op.drop_table('holidays')
