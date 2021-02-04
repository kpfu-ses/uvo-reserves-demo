from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse

from app.models import User, Project, Core, Coords, Logs
from app import app, db
from app.forms import LoginForm, RegistrationForm, ProjectForm, ProjectEditForm, \
    ResetPasswordRequestForm, ResetPasswordForm, EditProfileForm
from app.services import save_project, add_user, edit_project
from app.email import send_password_reset_email


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('profile')
        return redirect(next_page)
    return render_template('login.html', title='Log In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        add_user(form)
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', title='Reset Password', form=form)


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProjectForm()
    if form.validate_on_submit():
        save_project(form.name.data)
        return redirect(url_for('profile'))
    user = User.query.filter_by(username=current_user.username).first()
    projects = user.projects()
    return render_template('profile.html', title='Profile', form=form, projects=projects)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm(current_user.username)
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)


@app.route('/project/<name>', methods=['GET', 'POST'])
@login_required
def work_project(name):
    form = ProjectEditForm()
    project = Project.query.filter_by(name=name).first()
    if form.validate_on_submit():
        edit_project(form, project)
        return redirect(url_for('profile'))
    return render_template('project.html', title='Edit Project', project=project, form=form)


@app.route('/coords/<coords_id>', methods=['GET'])
@login_required
def coords(coords_id):
    coords = Coords.query.filter_by(id=coords_id).first()
    return render_template('coords.html', title='Coords', coords=coords)
