"""run

Revision ID: 781fc953db5f
Revises: 7390f0439d78
Create Date: 2021-02-05 15:07:37.003315

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '781fc953db5f'
down_revision = '7390f0439d78'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('run',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('date', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('run')
    # ### end Alembic commands ###