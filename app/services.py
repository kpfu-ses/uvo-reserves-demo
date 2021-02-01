from app.models import User, Project, Coords, Core, Logs
from app import app, db
from flask_login import current_user
from flask import flash

from app.models import projects_users

import os


def save_project(project_name):
    user = User.query.filter_by(username=current_user.username).first()
    project = Project(name=project_name)
    db.session.add(project)
    db.session.commit()

    project = Project.query.filter_by(name=project_name).first()
    statement = projects_users.insert().values(user_id=user.id,
                                               project_id=project.id,
                                               access='r')
    db.session.execute(statement)
    db.session.commit()


def edit_project(form, project):
    if form.name.data != '':
        project.name = form.name.data
    if form.coords_file.data.filename != '':
        file = form.coords_file.data
        filename = str(project.id) + '_coords_' + file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        coords = Coords(project_id=project.id, filepath=filename)
        db.session.add(coords)
    if form.core_file.data.filename != '':
        file = form.core_file.data
        filename = str(project.id) + '_core_' + file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        core = Core(project_id=project.id, filepath=filename)
        db.session.add(core)
    if form.logs_file.data.filename != '':
        file = form.logs_file.data
        filename = str(project.id) + '_logs_' + file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        logs = Logs(project_id=project.id, filepath=filename)
        db.session.add(logs)
    db.session.commit()


def add_user(form):
    user = User(username=form.username.data, email=form.email.data)
    user.set_password(form.password.data)
    db.session.add(user)
    db.session.commit()
    flash('Congratulations, you are now a registered user!')