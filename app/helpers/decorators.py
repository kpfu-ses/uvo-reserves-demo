from functools import wraps

from flask_jwt_extended import get_jwt_identity
from flask_login import current_user

from app.api.errors import bad_request
from app.models import User, Project, Run


def current_user_access():
    """This function checks if demanded page belongs to current user
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(user_id):
            if int(user_id) != int(current_user.id):
                return bad_request('this is not your profile')
            return f(user_id)
        return decorated_function
    return decorator


def user_project_access():
    """This function checks if demanded page belongs to current user
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(project_id):
            username = get_jwt_identity()['username']
            user = User.query.filter_by(username=username).first()
            project = Project.query.get(project_id)
            if project not in user.projects():
                return bad_request('this is not your project')
            return f(project_id)
        return decorated_function
    return decorator


# TODO
def user_run_access():
    """This function checks if demanded page belongs to current user
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(run_id):
            username = get_jwt_identity()['username']
            user = User.query.filter_by(username=username).first()
            run = Run.query.get(run_id)
            project = Project.query.get(run.project_id)
            if project not in user.projects():
                return bad_request('this is not your project')
            return f(run)
        return decorated_function
    return decorator
