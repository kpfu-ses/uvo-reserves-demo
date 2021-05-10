import json

from flask import request, make_response
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.api import bp
from app.helpers.util import default
from app.models import User
from app.services.project import save_project


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
    save_project(user, request.args.get('name'))
    return make_response('', 204)


