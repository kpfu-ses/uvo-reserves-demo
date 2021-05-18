from flask import request, jsonify, flash, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.api import bp
from app.microservices.main import get_wells_list
from app.models import User, Project
from app.helpers.services import save_run


# получение списка запусков проекта
@bp.route('/<project_id>/runs', methods=['GET'])
@jwt_required(locations=['cookies'])
def get_runs(project_id):
    project_runs = Project.query.get(project_id).runs().all()
    return {
        'runs': [run.serialize for run in project_runs]
    }


# создание запуска
@bp.route('/<project_id>/run', methods=['POST'])
@jwt_required(locations=['cookies'])
def create_run(project_id):
    run = save_run(project_id=project_id)
    return run.serialize


# выбор программных модулей
@bp.route('/runs/services', methods=['POST'])
@jwt_required(locations=['cookies'])
def choose_services():
    print(dict(request.json))
    return jsonify({
        'wells': get_wells_list(
            request.json['services'],
            request.json['run_id']
        )
    })


# выбор скважин
@bp.route('/runs/wells', methods=['POST'])
@jwt_required(locations=['cookies'])
def services_run():
    username = get_jwt_identity()['username']
    user = User.query.filter_by(username=username).first()
    if user.get_task_in_progress('run_services_task_bar'):
        flash('An export task is currently in progress')
    else:
        user.launch_task('run_services_task_bar',
                         'Running services...',
                         user.id, request.form['wells'],
                         request.form['services'],
                         request.form['run_id'])
        db.session.commit()
    return make_response('', 204)
