"""struct type

Revision ID: 5558c54ca99f
Revises: c9afe6a7c9eb
Create Date: 2021-03-21 09:28:36.357550

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5558c54ca99f'
down_revision = 'c9afe6a7c9eb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('struct_file', sa.Column('type', sa.Enum('RESERVES', 'SURF_TOP', 'SURF_BOT', 'GRID', 'GRID_FES', name='struct'), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('struct_file', 'type')
    # ### end Alembic commands ###