from flask import render_template, flash, redirect, url_for

from app import app
from app.forms import LoginForm


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        flash('Login requested for user {}, remember_me={}'.format(
            form.username.data, form.remember_me.data))
        return redirect(url_for('profile', username=form.username.data))
    return render_template('login.html', title='Log In', form=form)


@app.route('/profile/<string:username>')
def profile(username):
    return render_template('profile.html', title='Profile', username=username)
