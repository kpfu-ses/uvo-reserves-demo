from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.urls import url_parse

from app.models import User, Project
from app import app, db
from app.forms import LoginForm, RegistrationForm, ProjectForm, ProjectEditForm
from app.services import save_project, add_user, edit_project
from app.dto import ProjectFiles


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


@app.route('/project/<name>', methods=['GET', 'POST'])
@login_required
def work_project(name):
    form = ProjectEditForm()
    project = Project.query.filter_by(name=name).first()
    if form.validate_on_submit():
        edit_project(form, project)
        return redirect(url_for('profile'))
    return render_template('project.html', project=project, form=form, project_files=ProjectFiles(project))
