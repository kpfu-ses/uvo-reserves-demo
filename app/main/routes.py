from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import current_user, login_required
from datetime import datetime

from app import db
from app.helpers.services import save_project, edit_project, save_run
from app.main import bp
from app.main.forms import ProjectForm, ProjectEditForm, \
    EditProfileForm, RunForm
from app.microservices.main import get_wells_list
from app.models import User, Project, Coords, Run, Stratigraphy, Core, Notification


@bp.route('/')
@bp.route('/index')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('main.profile'))
    return render_template('index.html')


@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    current_user.last_run_see_time = datetime.now()
    db.session.commit()
    form = ProjectForm()
    if form.validate_on_submit():
        save_project(form.name.data)
        return redirect(url_for('main.profile'))
    user = User.query.filter_by(username=current_user.username).first()
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
        edit_project(form, project)
        return redirect(url_for('main.work_project', project_id=project_id))
    return render_template('project.html', title='Edit Project', project=project, form=form)


@bp.route('/coords/<coords_id>', methods=['GET'])
@login_required
def coords(coords_id):
    return render_template('coords.html', title='Coords', coords=Coords.query.get(coords_id))


@bp.route('/runs/services', methods=['POST'])
@login_required
def choose_services():
    return jsonify({'wells': get_wells_list(request.form['services'], request.form['run_id'])})


@bp.route('/runs/<run_id>', methods=['GET', 'POST'])
@login_required
def run(run_id):
    this_run = Run.query.get(run_id)
    if this_run.exist():
        return redirect(url_for('main.run_view', run_id=this_run.id))
    return render_template('run.html', title='Run', run=this_run)


@bp.route('/runs/wells', methods=['POST'])
@login_required
def services_run():
    if current_user.get_task_in_progress('run_services'):
        flash('An export task is currently in progress')
    else:
        current_user.launch_task('run_services_task', 'Running services...', current_user.id, request.form['wells'],
                                 request.form['services'], request.form['run_id'])
        db.session.commit()
    return jsonify({'okay': 'okay'})


@bp.route('/run_view/<run_id>', methods=['GET'])
@login_required
def run_view(run_id):
    this_run = Run.query.filter_by(id=run_id).first()
    strats = list(Stratigraphy.query.filter_by(run_id=this_run.id))
    core_res = list(Core.query.filter_by(run_id=this_run.id))
    return render_template('run_view.html', title='Run', strats=strats, core_res=core_res)


@bp.route('/<project_id>/runs', methods=['GET', 'POST'])
@login_required
def runs(project_id, done=False):
    form = RunForm()
    project_runs = Project.query.get(project_id).runs()
    if form.validate_on_submit():
        this_run = save_run(project_id=project_id)
        return redirect(url_for('main.run', run_id=this_run.id))
    return render_template('runs.html', title='Runs', form=form, project_runs=project_runs)


@bp.route('/runs/done', methods=['GET'])
@login_required
def done_runs():
    done_runs_list = current_user.new_runs()
    return render_template('done_runs.html', title='Done runs', runs=done_runs_list)


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
