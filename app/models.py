from app import db
from app import login

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

projects_users = db.Table("projects_users",
                          db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                          db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
                          db.Column('access', db.String(128))
                          )


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
        projects = Project.query.join(projects_users, projects_users.c.project_id == Project.id)\
            .filter(projects_users.c.user_id == self.id).all()
        return projects


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

    def __repr__(self):
        return 'Project {}'.format(self.name)
