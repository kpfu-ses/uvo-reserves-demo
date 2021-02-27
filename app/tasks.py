from app import create_app
from rq import get_current_job
from app import db
from app.microservices.main import run_services
from app.models import Task, User
import sys

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


def run_services_task(user_id, wells_ids_str, services, run_id):
    try:
        _set_task_progress(0)
        run_services(user_id, wells_ids_str, services, run_id)
        _set_task_progress(100)
    except:
        _set_task_progress(100)
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
