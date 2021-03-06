"""remove reports

Revision ID: 2a33609375be
Revises: 6ad8798dbe34
Create Date: 2021-03-17 12:01:29.639379

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2a33609375be'
down_revision = '6ad8798dbe34'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('run', 'report_3')
    op.drop_column('run', 'report_2')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('run', sa.Column('report_2', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    op.add_column('run', sa.Column('report_3', sa.VARCHAR(length=255), autoincrement=False, nullable=True))
    # ### end Alembic commands ###
