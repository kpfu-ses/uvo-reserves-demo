from flask import render_template, flash, redirect, url_for, request, jsonify, current_app
from flask_login import current_user, login_required

from app import db
from app.helpers.services import save_project, edit_project, get_crvs
from app.main import bp
from app.main.forms import ProjectForm, ProjectEditForm, \
    EditProfileForm
from app.models import User, Project, Coords, Notification, Well



@bp.route('/')
@bp.route('/index')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.profile'))
    return render_template('index.html')


@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProjectForm()
    if form.validate_on_submit():
        save_project(form.name.data)
        return redirect(url_for('main.profile'))
    user = User.query.get(current_user.id)
    projects = user.projects()
    return render_template('profile.html', title='Profile', form=form, projects=projects)


@bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('main.profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)


@bp.route('/project/<project_id>', methods=['GET', 'POST'])
@login_required
def work_project(project_id):
    form = ProjectEditForm()
    project = Project.query.get(project_id)
    if form.validate_on_submit():
        errors = edit_project(form, project)
        if len(errors) > 0:
            return render_template('load_errors.html', title='Load Problems',
                                   errors=errors, project_id=project_id)
    return render_template('project.html', title='Edit Project', project=project, form=form)


@bp.route('/project/upload', methods=['POST'])
@login_required
def services_run():
    print("im here")
    if current_user.get_task_in_progress('upload_files_task'):
        flash('An export task is currently in progress')
    else:
        project = Project.query.get(request.form['project_id'])
        current_user.launch_task('upload_files_task', 'Uploading files...', request.form['form'],
                                 project, current_app)
        db.session.commit()
    return jsonify({'okay': 'okay'})


@bp.route('/coords/<coords_id>', methods=['GET'])
@login_required
def coords(coords_id):
    return render_template('coords.html', title='Coords', coords=Coords.query.get(coords_id))


@bp.route('/logs/<well_id>', methods=['GET'])
@login_required
def logs(well_id):
    crvs = get_crvs(well_id)
    well_name = Well.query.get(well_id).name
    return render_template('crv_list.html', title='Curves', crvs=crvs, well_name=well_name)


@bp.route('/notifications')
@login_required
def notifications():
    since = request.args.get('since', 0.0, type=float)
    notifications = current_user.notifications.filter(
        Notification.timestamp > since).order_by(Notification.timestamp.asc())
    return jsonify([{
        'name': n.name,
        'data': n.get_data(),
        'timestamp': n.timestamp
    } for n in notifications])
