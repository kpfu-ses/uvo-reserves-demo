from datetime import datetime
import numpy as np
import os

from flask import flash, current_app
from flask_login import current_user

from app import db
from app.helpers.parser import read_coords, read_lasio
from app.helpers.util import save_file, well_name_re, save_core_file
from app.models import User, Project, Coords, Core, Logs, Well, Run, Curve, StructFile
from app.models import projects_users
from app.helpers.LasParser import ImportLasFiles


def save_project(project_name):
    user = User.query.get(current_user.id)
    project = Project(name=project_name)
    db.session.add(project)
    db.session.flush()

    statement = projects_users.insert().values(user_id=user.id,
                                               project_id=project.id,
                                               access='r')
    db.session.execute(statement)
    db.session.commit()


def edit_project(form, project):
    errors = []
    if form.name.data != '':
        project.name = form.name.data
    for coords_file in form.coords_file.data:
        if coords_file.filename != '':
            file = coords_file
            filename = str(project.id) + '_coords_' + str(datetime.now()) + file.filename
            save_file(file, filename, current_app)
            coords = add_coords(filename, project.id)
            if coords is None:
                errors.append("Не удалось обработать файл с координатами с таким названием: {}"
                              .format(file.filename))
            else:
                db.session.add(coords)
    for core_file in form.core_file.data:
        if core_file.filename != '':
            file = core_file
            filename = str(project.id) + '_core_' + str(datetime.now()) + file.filename
            well_name = save_core_file(file, filename, current_app)
            well = Well.query.filter_by(project_id=project.id, name=well_name).first()
            core = Core(project_id=project.id, filepath=filename, well_data_id=file.filename.split('.')[0], well_id=well.id)
            db.session.add(core)
    unnamed_well = form.unnamed_well.data
    log_files = []
    for logs_file in form.logs_file.data:
        if logs_file.filename != '':
            file = logs_file
            filename = str(project.id) + '_logs_' + str(datetime.now()) + '_file_' + file.filename
            save_file(file, filename, current_app)
            log_files.append(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            # log = add_log(os.path.join(current_app.config['UPLOAD_FOLDER'], filename), project.id)
            # if log is None:
            #     errors.append("Не удалось обработать las-файл с таким названием: {}"
            #                   .format(file.filename))
            # else:
            #     db.session.add(log)
    importer = ImportLasFiles(log_files, project_id=project.id, unnamed_well=unnamed_well)
    incorrect_files = importer.import_data()
    errors.extend(incorrect_files)
    for surf_top_file in form.surf_top_file.data:
        if surf_top_file.filename != '':
            file = surf_top_file
            filename = str(project.id) + '_surf_top_' + str(datetime.now()) + surf_top_file.filename
            save_file(file, filename, current_app)
            struct = StructFile(project_id=project.id, filepath=filename, type='SURF_TOP')
            if struct is None:
                errors.append("Не удалось обработать файл с поверхностью сетки с таким названием: {}"
                              .format(file.filename))
            else:
                db.session.add(struct)
    for surf_bot_file in form.surf_bot_file.data:
        if surf_bot_file.filename != '':
            file = surf_bot_file
            filename = str(project.id) + '_surf_bot_' + str(datetime.now()) + surf_bot_file.filename
            save_file(file, filename, current_app)
            struct = StructFile(project_id=project.id, filepath=filename, type='SURF_BOT')
            if struct is None:
                errors.append("Не удалось обработать файл с поверхностью сетки с таким названием: {}"
                              .format(file.filename))
            else:
                db.session.add(struct)
    for grid_file in form.grid_file.data:
        if grid_file.filename != '':
            file = grid_file
            filename = str(project.id) + '_grid_' + str(datetime.now()) + grid_file.filename
            save_file(file, filename, current_app)
            struct = StructFile(project_id=project.id, filepath=filename, type='GRID')
            if struct is None:
                errors.append("Не удалось обработать файл сетки с таким названием: {}"
                              .format(file.filename))
            else:
                db.session.add(struct)
    for grid_fes_file in form.grid_fes_file.data:
        if grid_fes_file.filename != '':
            file = grid_fes_file
            filename = str(project.id) + '_grid_fes_' + str(datetime.now()) + grid_fes_file.filename
            save_file(file, filename, current_app)
            struct = StructFile(project_id=project.id, filepath=filename, type='GRID_FES')
            if struct is None:
                errors.append("Не удалось обработать файл сетки с таким названием: {}"
                              .format(file.filename))
            else:
                db.session.add(struct)


    db.session.commit()
    return errors


def add_user(form):
    user = User(username=form.username.data, email=form.email.data)
    user.set_password(form.password.data)
    db.session.add(user)
    db.session.commit()
    flash('Congratulations, you are now a registered user!')


def add_coords(filepath, project_id):
    try:
        data = read_coords(filepath)
    except:
        return None
    well_name = well_name_re(data['Well'])
    # well_name = data['Well']
    well = check_well(well_name, project_id)
    coords = Coords(project_id=project_id, filepath=filepath, x=data['X'],
                    y=data['Y'], rkb=data['RKB'], well_id=well.id)
    return coords


def add_log(filepath, project_id):
    try:
        data = read_lasio(filepath)
    except:
        return None
    well = check_well(data['name'], project_id)

    for crv_name in data.keys():
        if (crv_name == 'name') or (crv_name == 'DEPT'):
            continue
        else:
            bottom = np.nanmin(data[crv_name])
            if bottom is not None:
                top = np.nanmax(data[crv_name])

                crv = db.session.query(Curve)\
                    .filter(Curve.well_id == well.id)\
                    .filter(Curve.name == crv_name)\
                    .first()
                if crv is None:
                    crv = Curve(project_id=project_id, well_id=well.id, name=crv_name,
                            top=top, bottom=bottom, data=data[crv_name])
                crv.data = data[crv_name]
                db.session.add(crv)

    db.session.commit()

    log = Logs(project_id=project_id, filepath=filepath, well_id=well.id)
    return log


def check_well(well_id, project_id):
    well = db.session.query(Well) \
            .filter(Well.name == well_id) \
            .filter(Well.project_id == project_id) \
            .first()
    if well is None:
        well = Well(name=well_id, project_id=project_id)
        db.session.add(well)
        db.session.commit()
    return well


def save_run(project_id):
    run = Run(project_id=project_id, date=datetime(1900, 1, 1))
    db.session.add(run)
    db.session.commit()
    return run


def get_crvs(well_id):
    return list(Curve.query.filter_by(well_id=well_id).all())
