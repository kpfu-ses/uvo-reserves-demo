"""struct type NEW2

Revision ID: 37481c7a8915
Revises: 5558c54ca99f
Create Date: 2021-03-21 09:35:30.541041

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '37481c7a8915'
down_revision = '5558c54ca99f'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('dummy',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('type', sa.Enum('UVO_RESERVES', 'SURF_TOP', 'SURF_BOT', 'GRID', 'GRID_FES', name='struct'), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('dummy')
    # ### end Alembic commands ###
