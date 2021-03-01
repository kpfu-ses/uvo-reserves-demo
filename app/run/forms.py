from flask_wtf import FlaskForm
from wtforms import SubmitField


class RunForm(FlaskForm):
    submit = SubmitField('Новый запуск')
