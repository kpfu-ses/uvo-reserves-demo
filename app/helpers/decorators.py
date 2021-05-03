from flask_login import current_user
from functools import wraps
from app.api.errors import bad_request


def current_user_access():
    """This function checks if demanded page belongs to current user
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(user_id):
            if int(user_id) != int(current_user.id):
                return bad_request('that is not your profile')
            return f(user_id)
        return decorated_function
    return decorator
