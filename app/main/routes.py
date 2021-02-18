from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import current_user, login_required

from app import db
from app.helpers.services import save_project, edit_project, save_run
from app.main import bp
from app.main.forms import ProjectForm, ProjectEditForm, \
    EditProfileForm, RunForm
from app.microservices.main import run_services, get_wells_list
from app.models import User, Project, Coords, Run, Stratigraphy


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


@bp.route('/project/<name>', methods=['GET', 'POST'])
@login_required
def work_project(name):
    form = ProjectEditForm()
    project = Project.query.filter_by(name=name).first()
    if form.validate_on_submit():
        edit_project(form, project)
        return redirect(url_for('main.profile'))
    return render_template('project.html', title='Edit Project', project=project, form=form, form2=RunForm())


@bp.route('/coords/<coords_id>', methods=['GET'])
@login_required
def coords(coords_id):
    coords = Coords.query.filter_by(id=coords_id).first()
    return render_template('coords.html', title='Coords', coords=coords)


@bp.route('/runs/services', methods=['POST'])
@login_required
def choose_services():
    if 'wells' in request.form:
        run_services(request.form['wells'], request.form['services'], request.form['run_id'])
    return jsonify({'wells': get_wells_list(request.form['services'], request.form['run_id'])})


@bp.route('/runs/<run_id>', methods=['GET', 'POST'])
@login_required
def run(run_id):
    this_run = Run.query.filter_by(id=run_id).first()
    if this_run.exist():
        return redirect(url_for('main.run_view', run_id=this_run.id))
    return render_template('run.html', title='Run', run=this_run)


@bp.route('/runs/wells', methods=['POST'])
@login_required
def services_run():
    run_services(request.form['wells'], request.form['services'], request.form['run_id'])
    return jsonify({'okay': 'okay'})


@bp.route('/project/<project_id>/new_run', methods=['GET', 'POST'])
def create_run(project_id):
    form = RunForm()
    project_name = Project.query.filter_by(id=project_id).first().name
    if form.validate_on_submit():
        run = save_run(project_id=project_id)
        return redirect(url_for('main.run', run_id=run.id))
    return redirect(url_for('main.work_project', name=project_name))


@bp.route('/run_view/<run_id>', methods=['GET'])
@login_required
def run_view(run_id):
    this_run = Run.query.filter_by(id=run_id).first()
    strats = list(Stratigraphy.query.filter_by(run_id=this_run.id))
    return render_template('run_view.html', title='Run', strats=strats)
