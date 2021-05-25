from flask import request, jsonify, flash, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.api import bp
from app.helpers.decorators import user_project_access, user_run_access
from app.microservices.main import get_wells_list
from app.models import User, Project, Run
from app.helpers.services import save_run
from app.services.run import get_data


# получение списка запусков проекта
@bp.route('/<project_id>/runs', methods=['GET'])
@jwt_required(locations=['cookies'])
@user_project_access()
def get_runs(project_id):
    project_runs = Project.query.get(project_id).runs().all()
    return {
        'runs': [run.serialize for run in project_runs]
    }


# создание запуска
@bp.route('/<project_id>/run', methods=['POST'])
@jwt_required(locations=['cookies'])
@user_project_access()
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
    print(request.json['wells'])
    username = get_jwt_identity()['username']
    user = User.query.filter_by(username=username).first()
    if user.get_task_in_progress('run_services_task_bar'):
        flash('An export task is currently in progress')
    else:
        user.launch_task('run_services_task_bar',
                         'Running services...',
                         user.id, request.json['wells'],
                         request.json['services'],
                         request.json['run_id'])
        db.session.commit()
    return make_response('', 204)


# результаты запуска
@bp.route('/runs/<run_id>', methods=['GET'])
@jwt_required(locations=['cookies'])
# @user_run_access()
def run_view(run_id):
    run = Run.query.get(run_id)
    if run.exist():
        data = get_data(run)
        return jsonify(data)
    else:
        return make_response('In progress', 200)
