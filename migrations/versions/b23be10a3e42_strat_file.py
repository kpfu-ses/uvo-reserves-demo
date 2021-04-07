"""strat file --

Revision ID: b23be10a3e42
Revises: d11feb3191e0
Create Date: 2021-03-21 09:14:11.810810

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b23be10a3e42'
down_revision = 'd11feb3191e0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('try')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('try',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.PrimaryKeyConstraint('id', name='try_pkey')
    )
    # ### end Alembic commands ###
