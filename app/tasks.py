import os
import shutil
import sys
from datetime import datetime

from flask import current_app
from rq import get_current_job

from app import create_app
from app import db
from app.helpers.LasParser import ImportLasFiles
from app.helpers.services import add_coords
from app.microservices.eighth import run_eighth
from app.microservices.fifth import run_fifth
from app.microservices.first import run_first
from app.microservices.main import run_services
from app.microservices.second import run_second
from app.microservices.seventh import run_seventh
from app.microservices.sixth import run_sixth
from app.microservices.third import run_third
from app.models import Task, User, Well, Run, ErrorFile, Core
from app.models import run_well

app = create_app()
app.app_context().push()


def _set_task_progress(progress):
    job = get_current_job()
    if job:
        job.meta['progress'] = progress
        job.save_meta()
        task = Task.query.get(job.get_id())
        user = User.query.get(task.user_id)
        user.add_notification('task_progress', {'task_id': job.get_id(),
                                                'progress': progress})
        if progress >= 100:
            task.complete = True
        db.session.commit()
    return progress


def run_services_task(user_id, wells_ids_str, services, run_id):
    print(wells_ids_str)
    try:
        _set_task_progress(0)
        run_services(user_id, wells_ids_str, services, run_id)
        _set_task_progress(100)
    except:
        _set_task_progress(100)
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())


def run_services_task_bar(user_id, wells_ids_str, services, run_id):
    print(wells_ids_str)
    try:
        gemeinsam_score = len(services.split(','))
        part = 100 // gemeinsam_score
        curr_progress = 0

        _set_task_progress(curr_progress)

        wells_ids = wells_ids_str.split(',')
        wells = Well.query.filter(Well.id.in_(wells_ids)).all()
        for well_id in wells_ids:
            statement = run_well.insert().values(well_id=well_id,
                                                 run_id=run_id, )
            db.session.execute(statement)

        db.session.commit()
        rep_serv = ''
        if '1' in services:
            wells = run_first(wells, run_id)
            rep_serv = 'first/'
            curr_progress = _set_task_progress(curr_progress + part)

        if '2' in services:
            wells = run_second(wells, run_id)
            if rep_serv == '':
                rep_serv = 'second/'
            curr_progress = _set_task_progress(curr_progress + part)

        if '3' in services:
            wells = run_third(wells, run_id)
            if rep_serv == '':
                rep_serv = 'third/'
            curr_progress = _set_task_progress(curr_progress + part)

        if '5' in services:
            run_fifth(wells, run_id)
            if rep_serv == '':
                rep_serv = 'fifth/'
            curr_progress = _set_task_progress(curr_progress + part)

        if '6' in services:
            run_sixth(run_id)
            if rep_serv == '':
                rep_serv = 'sixth/'
            curr_progress = _set_task_progress(curr_progress + part)

        if '7' in services:
            run_seventh(wells, run_id)
            if rep_serv == '':
                rep_serv = 'seventh/'
            curr_progress = _set_task_progress(curr_progress + part)

        if '8' in services:
            run_eighth(run_id)
            if rep_serv == '':
                rep_serv = 'eighth/'
            curr_progress = _set_task_progress(curr_progress + part)

        user = User.query.get(user_id)
        user.add_notification('done', len(user.new_runs()))
        db.session.commit()

        # updating run time for notifications
        run = Run.query.filter_by(id=run_id).first()
        run.date = datetime.now()

        # saving report_file
        report_filepath = current_app.config['SERVICES_PATH'] + rep_serv + str(
            run_id) + '/output_data/Report.txt'
        new_report_filepath = 'report_1_{}_Report.txt'.format(run_id)
        shutil.copyfile(report_filepath, "app/static/" + new_report_filepath)
        run.report_1 = new_report_filepath
        db.session.commit()

        _set_task_progress(100)
    except:
        _set_task_progress(100)
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())


def upload_files_task(files, unnamed_well, project, current_app):
    try:
        print('started uploading files')
        gemeinsam_score = len(files['coords']) + len(files['logs']) + len(files['core'])
        part = 100 // gemeinsam_score
        curr_progress = 0
        _set_task_progress(curr_progress)
        for coords_file in files['coords']:
            if coords_file != '':
                filename = coords_file
                coords = add_coords(filename, project.id)
                if coords is None:
                    error_file = ErrorFile(project_id=project.id,
                                           filename=filename,
                                           comment="Не удалось обработать файл с "
                                                   "координатами с таким "
                                                   "названием: {} "
                                           .format(filename))
                    db.session.add(error_file)
                else:
                    db.session.add(coords)
            curr_progress = _set_task_progress(curr_progress + part)
        for core_file in files['coords']:
            if core_file['file'] != '':
                filename = core_file['file']
                well_name = core_file['well_name']
                if well_name is None:
                    error_file = ErrorFile(project_id=project.id,
                                           filename=filename,
                                           comment="Не удалось обработать файл с "
                                                   "керн с таким "
                                                   "названием: {} "
                                           .format(filename))
                    db.session.add(error_file)
                else:
                    well = Well.query.filter_by(project_id=project.id,
                                                name=well_name).first()
                    if well is None:
                        well = Well(project_id=project.id, name=well_name)
                        db.session.add(well)
                        db.session.flush()
                    well.well_id = filename.split('.')[0]

                    core = Core(project_id=project.id, filepath=filename,
                                well_data_id=well.well_id, well_id=well.id)
                    db.session.add(core)
            curr_progress = _set_task_progress(curr_progress + part)
        log_files = []
        for logs_file in files['logs']:
            if logs_file != '':
                filename = logs_file
                log_files.append(
                    os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
            curr_progress = _set_task_progress(curr_progress + part)
        importer = ImportLasFiles(log_files, project_id=project.id,
                                  unnamed_well=unnamed_well)
        incorrect_files = importer.import_data()
        for filename in incorrect_files:
            error_file = ErrorFile(project_id=project.id,
                                   filename=filename,
                                   comment="Не удалось обработать файл с "
                                           "кривыми с таким "
                                           "названием: {} "
                                   .format(filename))
            db.session.add(error_file)
        _set_task_progress(100)
        db.session.commit()
    except:
        _set_task_progress(100)
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
