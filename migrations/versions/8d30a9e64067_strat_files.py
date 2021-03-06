"""strat files

Revision ID: 8d30a9e64067
Revises: daa7480286e2
Create Date: 2021-03-18 09:15:10.659394

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8d30a9e64067'
down_revision = 'daa7480286e2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('stratigraphy', sa.Column('filepath', sa.String(length=128), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('stratigraphy', 'filepath')
    # ### end Alembic commands ###
