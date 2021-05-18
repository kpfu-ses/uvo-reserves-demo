from datetime import datetime

from app import db
from app import login
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects import postgresql

from time import time
import json
import jwt
from enum import Enum
import redis
import rq

Base = declarative_base()

projects_users = db.Table("projects_users",
                          db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                          db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
                          db.Column('access', db.String(128))
                          )

run_well = db.Table("run_well",
                    db.Column('well_id', db.Integer, db.ForeignKey('well.id'), primary_key=True),
                    db.Column('run_id', db.Integer, db.ForeignKey('run.id'), primary_key=True))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password = db.Column(db.String(128))
    confirmcode = db.Column(db.String(128))
    state = db.Column(db.String(128))
    notifications = db.relationship('Notification', backref='user',
                                    lazy='dynamic')

    last_run_see_time = db.Column(db.DateTime)

    def as_dict(self, include_email=False):
        data = {
            'id': self.id,
            'username': self.username,
        }
        if include_email:
            data['email'] = self.email
        return data

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    def projects(self):
        projects = Project.query.join(projects_users, projects_users.c.project_id == Project.id) \
            .filter(projects_users.c.user_id == self.id).all()
        return projects

    def get_reset_password_token(self, expires_in=600):
        return jwt.encode(
            {'reset_password': self.id, 'exp': time() + expires_in},
            current_app.config['SECRET_KEY'], algorithm='HS256') \
            # .decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            rec_id = jwt.decode(token, current_app.config['SECRET_KEY'],
                                algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(rec_id)

    def add_notification(self, name, data):
        self.notifications.filter_by(name=name).delete()
        n = Notification(name=name, payload_json=json.dumps(data), user_id=self.id)
        db.session.add(n)
        return n

    def new_runs(self):
        last_read_time = self.last_run_see_time or datetime(1900, 1, 1)
        project_ids = [project.id for project in self.projects()]
        return db.session.query(Run) \
            .filter(Run.project_id.in_(project_ids), Run.date > last_read_time) \
            .all()

    def launch_task(self, name, description, *args, **kwargs):
        rq_job = current_app.task_queue.enqueue('app.tasks.' + name, *args, **kwargs, job_timeout=3000)
        task = Task(id=rq_job.get_id(), name=name, description=description,
                    user_id=self.id)
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        return Task.query.filter_by(user_id=self.id, complete=False).all()

    def get_task_in_progress(self, name):
        return Task.query.filter_by(name=name, user_id=self.id,
                                    complete=False).first()

    def __repr__(self):
        return 'User {}'.format(self.username)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    users = db.relationship("User",
                            secondary=projects_users,
                            backref=db.backref('projects_users', lazy='dynamic'), lazy='dynamic'
                            )

    def as_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def coords(self):
        return Coords.query.filter_by(project_id=self.id)

    def core(self):
        return Core.query.filter_by(project_id=self.id)

    def logs(self):
        return Logs.query.filter_by(project_id=self.id)

    def strats(self):
        return Stratigraphy.query.filter_by(project_id=self.id)

    def wells(self):
        return Well.query.filter_by(project_id=self.id)

    def runs(self):
        return Run.query.filter_by(project_id=self.id)

    def surf_top_files(self):
        return StructFile.query.filter_by(project_id=self.id, type='SURF_TOP')

    def surf_bot_files(self):
        return StructFile.query.filter_by(project_id=self.id, type='SURF_BOT')

    def grid_files(self):
        return StructFile.query.filter_by(project_id=self.id, type='GRID')

    def grid_fes_files(self):
        return StructFile.query.filter_by(project_id=self.id, type='GRID_FES')

    def __repr__(self):
        return 'Project {}'.format(self.name)


class Well(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    well_id = db.Column(db.String(128), index=True)
    name = db.Column(db.String(128), index=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    # depth = db.Column(postgresql.ARRAY(db.Float))
    depth = db.Column(db.PickleType)

    def coords(self):
        return Coords.query.filter_by(well_id=self.id)

    def logs(self):
        return Logs.query.filter_by(well_id=self.id)

    def core(self):
        return Core.query.filter_by(well_id=self.id)

    def curves(self):
        return Curve.query.filter_by(well_id=self.id)

    def strats(self):
        return Stratigraphy.query.filter_by(well_id=self.id)


# координаты
class Coords(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    well_id = db.Column(db.Integer, db.ForeignKey('well.id'))
    run_id = db.Column(db.Integer, db.ForeignKey('run.id'))
    x = db.Column(db.Float)
    y = db.Column(db.Float)
    rkb = db.Column(db.Float)
    filepath = db.Column(db.String(128))

    def well(self):
        return Well.query.filter_by(id=self.well_id).first()


# керн
class Core(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    well_id = db.Column(db.Integer, db.ForeignKey('well.id'))
    well_data_id = db.Column(db.String(128))
    run_id = db.Column(db.Integer, db.ForeignKey('run.id'))
    num = db.Column(db.Integer)
    # интервал отбора керна
    interval_start = db.Column(db.Float)
    interval_end = db.Column(db.Float)
    # пористость
    porosity = db.Column(db.Float)
    # насыщение
    saturation = db.Column(db.Float)
    # место взятия образца по керну
    original_location = db.Column(db.Float)
    # битумонасыщенность весовая
    oil_saturation_weight = db.Column(db.Float)
    # битумонасыщенность объемная
    oil_saturation_volumetric = db.Column(db.Float)
    # плотность объемная
    bulk_density = db.Column(db.Float)
    # литотип
    litho_type = db.Column(db.Float)
    filepath = db.Column(db.String(128))

    res_filepath = db.Column(db.String(255))


# las
class Logs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    well_id = db.Column(db.Integer, db.ForeignKey('well.id'))
    filepath = db.Column(db.String(128))
    res_filepath = db.Column(db.String(255))
    run_id = db.Column(db.Integer, db.ForeignKey('run.id'))


# кривая
class Curve(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    well_id = db.Column(db.Integer, db.ForeignKey('well.id'))
    run_id = db.Column(db.Integer, db.ForeignKey('run.id'))
    name = db.Column(db.String(128))
    data = db.Column(db.PickleType)
    top = db.Column(db.Float)
    bottom = db.Column(db.Float)
    unit = db.Column(db.String(128))
    filename = db.Column(db.String(255))


# стратиграфия
class Stratigraphy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    well_id = db.Column(db.Integer, db.ForeignKey('well.id'))
    filepath = db.Column(db.String(128))
    run_id = db.Column(db.Integer, db.ForeignKey('run.id'))
    lingula_top = db.Column(db.Float)
    p2ss2_top = db.Column(db.Float)
    p2ss2_bot = db.Column(db.Float)

    def well(self):
        return Well.query.filter_by(id=self.well_id).first()


# прогон микросервисов
class Run(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    date = db.Column(db.DateTime)
    report_1 = db.Column(db.String(255))

    @property
    def serialize(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'date': str(self.date),
            'report_1': self.report_1
        }

    def exist(self):
        stmt = db.select([run_well]).where(run_well.c.run_id == self.id)
        return len(db.session.execute(stmt).fetchall()) > 0


class Service(Enum):
    FIRST = 1
    SECOND = 2
    THIRD = 3


class Struct(Enum):
    UVO_RESERVES = 'UVO_RESERVES'
    SURF_TOP = 'SURF_TOP'
    SURF_BOT = 'SURF_BOT'
    GRID = 'GRID'
    GRID_FES = 'GRID_FES'


class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    complete = db.Column(db.Boolean, default=False)

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, connection=current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100


class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.Float, index=True, default=time)
    payload_json = db.Column(db.Text)

    def get_data(self):
        return json.loads(str(self.payload_json))


class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey('run.id'))
    service = db.Column(db.Integer)
    filepath = db.Column(db.String(255))


class StructFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    run_id = db.Column(db.Integer, db.ForeignKey('run.id'))
    type = db.Column(db.String(128))
    filepath = db.Column(db.String(255))


class ErrorFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(128))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    comment = db.Column(db.String(128))
