"""core num

Revision ID: 7390f0439d78
Revises: 59e32e55e500
Create Date: 2021-02-05 15:03:05.577561

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7390f0439d78'
down_revision = '59e32e55e500'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('core', sa.Column('num', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('core', 'num')
    # ### end Alembic commands ###
