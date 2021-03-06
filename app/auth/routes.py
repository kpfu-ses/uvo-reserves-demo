from flask import render_template, flash, redirect, url_for, request
from flask_login import current_user, login_user, logout_user
from werkzeug.urls import url_parse

from app import db
from app.auth import bp
from app.auth.email import send_password_reset_email
from app.auth.forms import LoginForm, RegistrationForm, ResetPasswordRequestForm, ResetPasswordForm
from app.models import User
from app.helpers.services import add_user


# @bp.route('/login', methods=['GET', 'POST'])
# def login():
#     if current_user.is_authenticated:
#         return redirect(url_for('main.profile'))
#     form = LoginForm()
#     if form.validate_on_submit():
#         user = User.query.filter_by(username=form.username.data).first()
#         if user is None or not user.check_password(form.password.data):
#             flash('Invalid username or password')
#             return redirect(url_for('auth.login'))
#         login_user(user, remember=form.remember_me.data)
#         next_page = request.args.get('next')
#         if not next_page or url_parse(next_page).netloc != '':
#             next_page = url_for('main.profile')
#         return redirect(next_page)
#     return render_template('auth/login.html', title='Log In', form=form)


@bp.route('/login', methods=['GET'])
def login():
    access_token = request.cookies.get('access_token', None)
    if access_token is not None:
        return redirect(url_for('api.get_profile'), 302)
    return render_template('auth/login.html', title='Log In', form=LoginForm())


@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


# @bp.route('/register', methods=['GET', 'POST'])
# def register():
#     if current_user.is_authenticated:
#         return redirect(url_for('main.index'))
#     form = RegistrationForm()
#     if form.validate_on_submit():
#         add_user(form)
#         return redirect(url_for('auth.login'))
#     return render_template('auth/register.html', title='Register', form=form)


@bp.route('/register', methods=['GET'])
def register():
    access_token = request.cookies.get('access_token', None)
    if access_token is not None:
        return redirect(url_for('api.get_profile'), 302)
    return render_template('auth/register.html', title='Register', form=RegistrationForm())


@bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.profile'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password_request.html',
                           title='Reset Password', form=form)


@bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('main.index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('auth/reset_password.html', title='Reset Password', form=form)

