from flask import request, jsonify, flash, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db
from app.api import bp
from app.microservices.main import get_wells_list
from app.models import User


# выбор программных модулей
@bp.route('/runs/services', methods=['POST'])
@jwt_required(locations=['cookies'])
def choose_services():
    return jsonify({'wells': get_wells_list(request.form['services'],
                                            request.form['run_id'])})


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
