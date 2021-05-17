import os
import uuid
import time
import numpy as np

from flask import current_app

from app import db
from app.helpers.LasParser import ImportLasFiles
from app.helpers.parser import read_coords, read_lasio
from app.helpers.util import save_file, well_name_re, save_core_file
from app.models import Project, Coords, Core, Logs, Well, Curve
from app.models import projects_users


def save_project(user, project_name):
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
    if form.name != '':
        project.name = form.name.data
    print(form.coords_file)
    for coords_file in form.coords_file:
        print(coords_file)
        if coords_file.filename != '':
            file = coords_file
            filename = str(project.id) + '_coords_' + str(round(time.time() * 1000)) + file.filename
            save_file(file, filename, current_app)
            coords = add_coords(filename, project.id)
            if coords is None:
                errors.append("Не удалось обработать файл с координатами с таким названием: {}"
                              .format(file.filename))
            else:
                db.session.add(coords)
    for core_file in form.core_file:
        if core_file.filename != '':
            file = core_file
            filename = str(project.id) + '_core_' + str(uuid.uuid4())
            well_name = save_core_file(file, filename, current_app)
            if well_name is None:
                errors.append(
                    "Не удалось обработать файл с керн с таким названием: {}"
                    .format(file.filename))
            else:
                well = Well.query.filter_by(project_id=project.id, name=well_name).first()
                if well is None:
                    well = Well(project_id=project.id, name=well_name)
                    db.session.add(well)
                    db.session.flush()
                well.well_id = file.filename.split('.')[0]

                core = Core(project_id=project.id, filepath=filename, well_data_id=well.well_id, well_id=well.id)
                db.session.add(core)
    unnamed_well = ''
    log_files = []
    for logs_file in form.logs_file:
        if logs_file.filename != '':
            file = logs_file
            filename = str(project.id) + '_logs_' + str(uuid.uuid4()) + '_file_' + file.filename
            save_file(file, filename, current_app)
            log_files.append(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
    importer = ImportLasFiles(log_files, project_id=project.id, unnamed_well=unnamed_well)
    incorrect_files = importer.import_data()
    errors.extend(incorrect_files)
    db.session.commit()
    return errors


def add_coords(filepath, project_id):
    try:
        data = read_coords(filepath)
        well_name = well_name_re(data['Well'])
        well = check_well(well_name, project_id)
        coords = Coords(project_id=project_id, filepath=filepath, x=data['X'],
                        y=data['Y'], rkb=data['RKB'], well_id=well.id)
        return coords
    except:
        return None


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