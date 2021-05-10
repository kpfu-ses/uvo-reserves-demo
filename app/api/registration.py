from flask import request

from app.api import bp
from app.api.errors import bad_request
from app.services.auth import register_user


@bp.route('/register', methods=['POST'])
def register():
    try:
        username = request.json.get('username', None)
        password = request.json.get('password', None)
        email = request.json.get('email', None)
        return register_user(username, email, password)
    except AttributeError:
        return bad_request('Provide a data in JSON format in the request body')
