import json

from flask_login import current_user, login_required

from app.api import bp
from app.models import User
from app.helpers.services import save_project
from app.helpers.util import default
from flask import request, make_response


# profile
@bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    user = User.query.get(current_user.id)
    projects = user.projects()
    profile_info = {'user': user.as_dict(), 'projects': [p.as_dict() for p in projects]}
    return json.dumps(profile_info, default=default)


# adding new project
@bp.route('/project', methods=['POST'])
@login_required
def post_profile():
    save_project(request.args.get('name'))
    return make_response('', 204)


