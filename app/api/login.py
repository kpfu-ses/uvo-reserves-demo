from flask import request

from app.api import bp
from app.api.errors import bad_request
from app.services.auth import login_user


@bp.route('/login', methods=['POST'])
def login():
    try:
        username = request.json.get('username', None)
        password = request.json.get('password', None)
        return login_user(username, password)
    except AttributeError:
        return bad_request('Provide an Username and Password in JSON format in the request body')
