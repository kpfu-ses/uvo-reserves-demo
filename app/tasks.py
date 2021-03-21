from datetime import datetime

from app import create_app
from rq import get_current_job
from app import db
from app.microservices.main import run_services
from app.models import  Task, User, Project, Coords, Core, Logs, Well, Run, Curve, StructFile
from app.helpers.util import save_file, well_name_re
from app.helpers.services import add_coords, add_log
import sys
import os

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
    try:
        _set_task_progress(0)
        run_services(user_id, wells_ids_str, services, run_id)
        _set_task_progress(100)
    except:
        _set_task_progress(100)
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())


def upload_files_task(form, project, current_app):
    print('uploading')
    try:
        errors = []
        # gemeinsam_score = len(form.coords_file.data) + len(form.grid_file.data) \
        #                   + len(form.grid_fes_file.data) + len(form.core_file.data)\
        #                   + len(form.logs_file.data) + len(form.surf_top_file.data) \
        #                   + len(form.surf_bot_file.data)
        gemeinsam_score = len(form['coords_file']) + len(form['surf_top_file'])
        part = 100 // gemeinsam_score
        curr_progress = 0
        for coords_file in form['coords_file']:
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
            curr_progress = _set_task_progress(curr_progress + part)
        # for core_file in form.core_file.data:
        #     if core_file.filename != '':
        #         file = core_file
        #         filename = str(project.id) + '_core_' + str(datetime.now()) + file.filename
        #         save_file(file, filename, current_app)
        #         core = Core(project_id=project.id, filepath=filename, well_data_id=file.filename.split('.')[0])
        #         db.session.add(core)
        #     curr_progress = _set_task_progress(curr_progress + part)
        # for logs_file in form.logs_file.data:
        #     if logs_file.filename != '':
        #         file = logs_file
        #         filename = str(project.id) + '_logs_' + str(datetime.now()) + file.filename
        #         save_file(file, filename, current_app)
        #         log = add_log(os.path.join(current_app.config['UPLOAD_FOLDER'], filename), project.id)
        #         if log is None:
        #             errors.append("Не удалось обработать las-файл с таким названием: {}"
        #                           .format(file.filename))
        #         else:
        #             db.session.add(log)
        #     curr_progress = _set_task_progress(curr_progress + part)
        #
        for surf_top_file in form['surf_top_file']:
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
            curr_progress = _set_task_progress(curr_progress + part)
        #
        # for surf_bot_file in form.surf_bot_file.data:
        #     if surf_bot_file.filename != '':
        #         file = surf_bot_file
        #         filename = str(project.id) + '_surf_bot_' + str(datetime.now()) + surf_bot_file.filename
        #         save_file(file, filename, current_app)
        #         struct = StructFile(project_id=project.id, filepath=filename, type=Struct.SURF_BOT)
        #         if struct is None:
        #             errors.append("Не удалось обработать файл с поверхностью сетки с таким названием: {}"
        #                           .format(file.filename))
        #         else:
        #             db.session.add(struct)
        #     curr_progress = _set_task_progress(curr_progress + part)
        #
        # for grid_file in form.grid_file.data:
        #     if grid_file.filename != '':
        #         file = grid_file
        #         filename = str(project.id) + '_grid_' + str(datetime.now()) + grid_file.filename
        #         save_file(file, filename, current_app)
        #         struct = StructFile(project_id=project.id, filepath=filename, type=Struct.GRID)
        #         if struct is None:
        #             errors.append("Не удалось обработать файл сетки с таким названием: {}"
        #                           .format(file.filename))
        #         else:
        #             db.session.add(struct)
        #     curr_progress = _set_task_progress(curr_progress + part)
        #
        # for grid_fes_file in form.grid_fes_file.data:
        #     if grid_fes_file.filename != '':
        #         file = grid_fes_file
        #         filename = str(project.id) + '_grid_fes_' + str(datetime.now()) + grid_fes_file.filename
        #         save_file(file, filename, current_app)
        #         struct = StructFile(project_id=project.id, filepath=filename, type=Struct.GRID_FES)
        #         if struct is None:
        #             errors.append("Не удалось обработать файл сетки с таким названием: {}"
        #                           .format(file.filename))
        #         else:
        #             db.session.add(struct)
        #     curr_progress = _set_task_progress(curr_progress + part)

        db.session.commit()
        # return errors
    except:
        _set_task_progress(100)
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())