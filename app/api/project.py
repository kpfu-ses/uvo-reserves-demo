import json

from flask import request
from flask_jwt_extended import jwt_required

from app.api import bp
from app.forms.project_form import ProjectForm
from app.helpers.decorators import user_project_access
from app.helpers.util import default
from app.models import Project
from app.services.project import edit_project


@bp.route('/project/<project_id>', methods=['POST'])
@jwt_required(locations=['cookies'])
@user_project_access()
def work_project(project_id):
    logs_files = request.files.getlist("logs_files")
    core_files = request.files.getlist("core_files")
    coords_files = request.files.getlist("coords_files")
    # для редактирования имени
    name = request.args.get('name')
    project = Project.query.get(project_id)
    project_form = ProjectForm(name, logs_files, core_files, coords_files)
    # список ошибок, которые нужно отобразить пользователю
    errors = edit_project(project_form, project)
    return json.dumps(errors, default=default)

