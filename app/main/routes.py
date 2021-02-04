from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_required

from app.models import User, Project, Coords
from app import db
from app.main import bp
from app.main.forms import ProjectForm, ProjectEditForm, \
    EditProfileForm
from app.helper.services import save_project, edit_project


@bp.route('/')
@bp.route('/index')
def index():
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
    return render_template('project.html', title='Edit Project', project=project, form=form)


@bp.route('/coords/<coords_id>', methods=['GET'])
@login_required
def coords(coords_id):
    coords = Coords.query.filter_by(id=coords_id).first()
    return render_template('coords.html', title='Coords', coords=coords)