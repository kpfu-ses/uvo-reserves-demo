"""logs update

Revision ID: 192b6d9b530d
Revises: be3ae7baf82a
Create Date: 2021-03-08 16:30:57.053452

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '192b6d9b530d'
down_revision = 'be3ae7baf82a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('logs', sa.Column('res_filepath', sa.String(length=255), nullable=True))
    op.add_column('logs', sa.Column('run_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'logs', 'run', ['run_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'logs', type_='foreignkey')
    op.drop_column('logs', 'run_id')
    op.drop_column('logs', 'res_filepath')
    # ### end Alembic commands ###
