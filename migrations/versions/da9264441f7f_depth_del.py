"""depth del

Revision ID: da9264441f7f
Revises: d43bcef25dd2
Create Date: 2021-03-26 13:39:33.791547

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'da9264441f7f'
down_revision = 'd43bcef25dd2'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('well', 'depth')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('well', sa.Column('depth', postgresql.ARRAY(postgresql.DOUBLE_PRECISION(precision=53)), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
