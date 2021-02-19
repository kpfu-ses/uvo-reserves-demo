from app import db
from app import login
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy.ext.declarative import declarative_base

from time import time
import jwt
from enum import Enum, auto

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
            current_app.config['SECRET_KEY'], algorithm='HS256')\
            # .decode('utf-8')

    @staticmethod
    def verify_reset_password_token(token):
        try:
            rec_id = jwt.decode(token, current_app.config['SECRET_KEY'],
                                algorithms=['HS256'])['reset_password']
        except:
            return
        return User.query.get(rec_id)

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

    def coords(self):
        return Coords.query.filter_by(project_id=self.id)

    def core(self):
        return Core.query.filter_by(project_id=self.id)

    def logs(self):
        return Logs.query.filter_by(project_id=self.id)

    def wells(self):
        return Well.query.filter_by(project_id=self.id)

    def runs(self):
        return Run.query.filter_by(project_id=self.id)

    def __repr__(self):
        return 'Project {}'.format(self.name)


class Well(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))

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


# кривая
class Curve(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    well_id = db.Column(db.Integer, db.ForeignKey('well.id'))
    run_id = db.Column(db.Integer, db.ForeignKey('run.id'))
    name = db.Column(db.String(128))
    data = db.Column(db.Binary)
    top = db.Column(db.Float)
    bottom = db.Column(db.Float)


# стратиграфия
class Stratigraphy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    well_id = db.Column(db.Integer, db.ForeignKey('well.id'))
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

    def exist(self):
        stmt = db.select([run_well]).where(run_well.c.run_id == self.id)
        return len(db.session.execute(stmt).fetchall()) > 0


class Service(Enum):
    FIRST = 1
    SECOND = 2
    THIRD = 3



