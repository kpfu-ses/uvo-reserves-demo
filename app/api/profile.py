import json

from flask_login import current_user, login_required

from app.api import bp
from app.models import User
from app.helpers.decorators import current_user_access
from app.helpers.services import save_project
from flask import request, make_response


# profile
@bp.route('/users/<user_id>', methods=['GET'])
@login_required
@current_user_access()
def get_profile(user_id):
    user = User.query.get(user_id)
    projects = user.projects()
    return json.dumps([p.as_dict() for p in projects])


# adding new project
@bp.route('/users/<user_id>/project', methods=['POST'])
@login_required
@current_user_access()
def post_profile(user_id):
    save_project(request.args.get('name'))
    return make_response('', 204)


