"""empty message

Revision ID: 0589c58df68a
Revises: 
Create Date: 2021-05-25 18:45:07.059207

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0589c58df68a'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('project',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('user',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=True),
    sa.Column('email', sa.String(length=120), nullable=True),
    sa.Column('password', sa.String(length=128), nullable=True),
    sa.Column('confirmcode', sa.String(length=128), nullable=True),
    sa.Column('state', sa.String(length=128), nullable=True),
    sa.Column('last_run_see_time', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=True)
    op.create_index(op.f('ix_user_username'), 'user', ['username'], unique=True)
    op.create_table('error_file',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('filename', sa.String(length=128), nullable=True),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('comment', sa.String(length=128), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('notification',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('timestamp', sa.Float(), nullable=True),
    sa.Column('payload_json', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_notification_name'), 'notification', ['name'], unique=False)
    op.create_index(op.f('ix_notification_timestamp'), 'notification', ['timestamp'], unique=False)
    op.create_table('projects_users',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=False),
    sa.Column('access', sa.String(length=128), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('user_id', 'project_id')
    )
    op.create_table('run',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('date', sa.DateTime(), nullable=True),
    sa.Column('report_1', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('task',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.Column('description', sa.String(length=128), nullable=True),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('complete', sa.Boolean(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_task_name'), 'task', ['name'], unique=False)
    op.create_table('well',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('well_id', sa.String(length=128), nullable=True),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('depth', sa.PickleType(), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_well_name'), 'well', ['name'], unique=False)
    op.create_index(op.f('ix_well_well_id'), 'well', ['well_id'], unique=False)
    op.create_table('coords',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('well_id', sa.Integer(), nullable=True),
    sa.Column('run_id', sa.Integer(), nullable=True),
    sa.Column('x', sa.Float(), nullable=True),
    sa.Column('y', sa.Float(), nullable=True),
    sa.Column('rkb', sa.Float(), nullable=True),
    sa.Column('filepath', sa.String(length=128), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['run_id'], ['run.id'], ),
    sa.ForeignKeyConstraint(['well_id'], ['well.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('core',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('well_id', sa.Integer(), nullable=True),
    sa.Column('well_data_id', sa.String(length=128), nullable=True),
    sa.Column('run_id', sa.Integer(), nullable=True),
    sa.Column('num', sa.Integer(), nullable=True),
    sa.Column('interval_start', sa.Float(), nullable=True),
    sa.Column('interval_end', sa.Float(), nullable=True),
    sa.Column('porosity', sa.Float(), nullable=True),
    sa.Column('saturation', sa.Float(), nullable=True),
    sa.Column('original_location', sa.Float(), nullable=True),
    sa.Column('oil_saturation_weight', sa.Float(), nullable=True),
    sa.Column('oil_saturation_volumetric', sa.Float(), nullable=True),
    sa.Column('bulk_density', sa.Float(), nullable=True),
    sa.Column('litho_type', sa.Float(), nullable=True),
    sa.Column('filepath', sa.String(length=128), nullable=True),
    sa.Column('res_filepath', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['run_id'], ['run.id'], ),
    sa.ForeignKeyConstraint(['well_id'], ['well.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('core_results',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('well_id', sa.Integer(), nullable=True),
    sa.Column('run_id', sa.Integer(), nullable=True),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.ForeignKeyConstraint(['run_id'], ['run.id'], ),
    sa.ForeignKeyConstraint(['well_id'], ['well.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('curve',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('well_id', sa.Integer(), nullable=True),
    sa.Column('run_id', sa.Integer(), nullable=True),
    sa.Column('name', sa.String(length=128), nullable=True),
    sa.Column('data', sa.PickleType(), nullable=True),
    sa.Column('top', sa.Float(), nullable=True),
    sa.Column('bottom', sa.Float(), nullable=True),
    sa.Column('unit', sa.String(length=128), nullable=True),
    sa.Column('filename', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['run_id'], ['run.id'], ),
    sa.ForeignKeyConstraint(['well_id'], ['well.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('logs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('well_id', sa.Integer(), nullable=True),
    sa.Column('filepath', sa.String(length=128), nullable=True),
    sa.Column('res_filepath', sa.String(length=255), nullable=True),
    sa.Column('run_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['run_id'], ['run.id'], ),
    sa.ForeignKeyConstraint(['well_id'], ['well.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('result',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('run_id', sa.Integer(), nullable=True),
    sa.Column('service', sa.Integer(), nullable=True),
    sa.Column('filepath', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['run_id'], ['run.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('run_well',
    sa.Column('well_id', sa.Integer(), nullable=False),
    sa.Column('run_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['run_id'], ['run.id'], ),
    sa.ForeignKeyConstraint(['well_id'], ['well.id'], ),
    sa.PrimaryKeyConstraint('well_id', 'run_id')
    )
    op.create_table('stratigraphy',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('well_id', sa.Integer(), nullable=True),
    sa.Column('filepath', sa.String(length=128), nullable=True),
    sa.Column('run_id', sa.Integer(), nullable=True),
    sa.Column('lingula_top', sa.Float(), nullable=True),
    sa.Column('p2ss2_top', sa.Float(), nullable=True),
    sa.Column('p2ss2_bot', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['run_id'], ['run.id'], ),
    sa.ForeignKeyConstraint(['well_id'], ['well.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('struct_file',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('project_id', sa.Integer(), nullable=True),
    sa.Column('run_id', sa.Integer(), nullable=True),
    sa.Column('type', sa.String(length=128), nullable=True),
    sa.Column('filepath', sa.String(length=255), nullable=True),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['run_id'], ['run.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('struct_file')
    op.drop_table('stratigraphy')
    op.drop_table('run_well')
    op.drop_table('result')
    op.drop_table('logs')
    op.drop_table('curve')
    op.drop_table('core_results')
    op.drop_table('core')
    op.drop_table('coords')
    op.drop_index(op.f('ix_well_well_id'), table_name='well')
    op.drop_index(op.f('ix_well_name'), table_name='well')
    op.drop_table('well')
    op.drop_index(op.f('ix_task_name'), table_name='task')
    op.drop_table('task')
    op.drop_table('run')
    op.drop_table('projects_users')
    op.drop_index(op.f('ix_notification_timestamp'), table_name='notification')
    op.drop_index(op.f('ix_notification_name'), table_name='notification')
    op.drop_table('notification')
    op.drop_table('error_file')
    op.drop_index(op.f('ix_user_username'), table_name='user')
    op.drop_index(op.f('ix_user_email'), table_name='user')
    op.drop_table('user')
    op.drop_table('project')
    # ### end Alembic commands ###
