"""add pt assignment timing fields

Revision ID: adaa03cbb54b
Revises: a999dc4dceba
Create Date: 2026-07-28 15:14:39.763655

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'adaa03cbb54b'
down_revision = 'a999dc4dceba'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('assignments', schema=None) as batch_op:
        batch_op.add_column(sa.Column('start_time', sa.Time(), nullable=True))
        batch_op.add_column(sa.Column('end_time', sa.Time(), nullable=True))
        batch_op.add_column(sa.Column('duration_minutes', sa.Integer(), nullable=True))

    with op.batch_alter_table('assignment_selection_details', schema=None) as batch_op:
        batch_op.drop_constraint('ck_assignment_selection_details_service_code', type_='check')
        batch_op.create_check_constraint(
            'ck_assignment_selection_details_service_code',
            "service_code in ('AT1', 'AT2', 'AT3', 'PO1', 'PO2', 'PO3', 'PT')",
        )


def downgrade():
    with op.batch_alter_table('assignment_selection_details', schema=None) as batch_op:
        batch_op.drop_constraint('ck_assignment_selection_details_service_code', type_='check')
        batch_op.create_check_constraint(
            'ck_assignment_selection_details_service_code',
            "service_code in ('AT1', 'AT2', 'AT3', 'PO1', 'PO2', 'PO3')",
        )

    with op.batch_alter_table('assignments', schema=None) as batch_op:
        batch_op.drop_column('duration_minutes')
        batch_op.drop_column('end_time')
        batch_op.drop_column('start_time')
