"""logs well

Revision ID: eae98cb13c55
Revises: 97a842b8accd
Create Date: 2021-02-08 08:59:09.327707

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eae98cb13c55'
down_revision = '97a842b8accd'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('logs', sa.Column('well_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'logs', 'well', ['well_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'logs', type_='foreignkey')
    op.drop_column('logs', 'well_id')
    # ### end Alembic commands ###