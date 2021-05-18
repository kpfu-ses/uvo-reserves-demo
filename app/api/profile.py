import json

from flask import request, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.api import bp
from app.helpers.util import default
from app.models import User
from app.services.project import save_project
from app.services.profile import edit_profile


# profile
@bp.route('/profile', methods=['GET'])
@jwt_required(locations=['cookies'])
def get_profile():
    username = get_jwt_identity()['username']
    user = User.query.filter_by(username=username).first()
    projects = user.projects()
    profile_info = {'user': user.as_dict(), 'projects': [p.as_dict() for p in projects]}
    return json.dumps(profile_info, default=default)


# adding new project
@bp.route('/project', methods=['POST'])
@jwt_required(locations=['cookies'])
def post_profile():
    username = get_jwt_identity()['username']
    user = User.query.filter_by(username=username).first()
    project = save_project(user, request.json.get('name'))
    return {'projectId': project.id}


@bp.route('/edit_profile', methods=['GET', 'POST'])
@jwt_required(locations=['cookies'])
def edit_profile():
    username = get_jwt_identity()['username']
    user = User.query.filter_by(username=username).first()
    if request.method == 'POST':
        new_username = request.args.get('username')
        new_email = request.args.get('email')
        edit_profile(user, new_username, new_email)
        return make_response('', 204)
    elif request.method == 'GET':
        user_info = {'username': user.username, 'email': user.email}
    return json.dumps(user_info, default=default)
