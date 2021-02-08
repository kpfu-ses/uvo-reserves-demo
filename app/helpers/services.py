from app.models import User, Project, Coords, Core, Logs, Well, Run
from app import db
from flask_login import current_user
from flask import flash, current_app

from app.models import projects_users, run_well
from app.helpers.util import save_file
from app.helpers.parser import read_coords

from datetime import datetime
import shutil
import os
import subprocess
from pathlib import Path

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
    for coords_file in form.coords_file.data:
        if coords_file.filename != '':
            file = coords_file
            filename = str(project.id) + '_coords_' + str(datetime.now()) + file.filename
            save_file(file, filename, current_app)
            coords = add_coords(filename, project.id)
            db.session.add(coords)
    for core_file in form.core_file.data:
        if core_file.filename != '':
            file = core_file
            filename = str(project.id) + '_core_' + str(datetime.now()) + file.filename
            save_file(file, filename, current_app)
            core = Core(project_id=project.id, filepath=filename)
            db.session.add(core)
    for logs_file in form.logs_file.data:
        if logs_file.filename != '':
            file = logs_file
            filename = str(project.id) + '_logs_' + str(datetime.now()) + file.filename
            save_file(file, filename, current_app)
            logs = Logs(project_id=project.id, filepath=filename)
            db.session.add(logs)
    db.session.commit()


def add_user(form):
    user = User(username=form.username.data, email=form.email.data)
    user.set_password(form.password.data)
    db.session.add(user)
    db.session.commit()
    flash('Congratulations, you are now a registered user!')


def add_coords(filepath, project_id):
    data = read_coords(filepath)
    check_well(data['Well'], project_id)

    coords = Coords(project_id=project_id, filepath=filepath, x=data['X'],
                    y=data['Y'], rkb=data['RKB'], well_id=Well.query.filter_by(name=data['Well']).first().id)
    return coords


def check_well(well_id, project_id):
    if Well.query.filter_by(name=well_id).first() is None:
        db.session.add(Well(name=well_id, project_id=project_id))
        db.session.commit()


def run_wells(run, services):
    result = []
    if 1 in services:
        result = db.session.query(Well, Logs, Coords)\
            .filter(Well.project_id == run.project_id)\
            .filter(Logs.well_id == Well.id)\
            .filter(Coords.well_id == Well.id).distinct(Well.id).all()

    return [well for well, log, coords in result]


def save_run(project_id):
    run = Run(project_id=project_id, date=datetime.now())
    db.session.add(run)
    db.session.commit()
    return run


def run_services(wells_ids, services, run_id):
    wells = Well.query.filter(Well.id.in_(wells_ids)).all()
    for well_id in wells_ids:
        statement = run_well.insert().values(well_id=well_id, run_id=run_id,)
        db.session.execute(statement)

    db.session.commit()
    if 1 in services:
        for well in wells:
            for coords in well.coords():
                # os.system("mkdir ../modules/1/input_data/coords/" + well.name)
                Path("app/modules/1/input_data/coords/" + well.name).mkdir(parents=True, exist_ok=True)
                shutil.copyfile(os.path.join(current_app.config['UPLOAD_FOLDER'], coords.filepath),
                                'app/modules/1/input_data/coords/' + well.name + '/' + coords.filepath)
            for logs in well.logs():
                Path("app/modules/1/input_data/wellLogs/" + well.name).mkdir(parents=True, exist_ok=True)
                shutil.copyfile(os.path.join(current_app.config['UPLOAD_FOLDER'], logs.filepath),
                                'app/modules/1/input_data/wellLogs/' + well.name + '/' + logs.filepath)

    # subprocess.call("python3 app/modules/1/Strat_P2ss2.py 1", shell=True)
    os.system("python3 app/modules/1/Strat_P2ss2.py")