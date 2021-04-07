"""depth

Revision ID: d43bcef25dd2
Revises: cd4ef7b92966
Create Date: 2021-03-24 21:56:36.544858

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd43bcef25dd2'
down_revision = 'cd4ef7b92966'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('well', sa.Column('depth', postgresql.ARRAY(sa.Float()), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('well', 'depth')
    # ### end Alembic commands ###
