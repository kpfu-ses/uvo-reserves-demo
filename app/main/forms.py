from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, MultipleFileField, SelectMultipleField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from app.models import User, Well


class ProjectForm(FlaskForm):
    name = StringField('Название проекта', validators=[DataRequired()])
    submit = SubmitField('Добавить проект')


class ProjectEditForm(FlaskForm):
    name = StringField('Новое название проекта')
    coords_file = MultipleFileField('Загрузить координаты')
    core_file = MultipleFileField('Загрузить керн')
    logs_file = MultipleFileField('Загрузить кривые')
    submit = SubmitField('Редактировать проект')


class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])

    submit = SubmitField('Edit')

    def __init__(self, original_username, *args, **kwargs):
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username.data != self.original_username:
            user = User.query.filter_by(username=self.username.data).first()
            if user is not None:
                raise ValidationError('Please use a different username.')


class ChooseServicesForm(FlaskForm):
    services = SelectMultipleField('Выберите програмнные модули для запуска',
                                   choices=[(1, "1 СВН ОТБИВКИ"), (2, "2 СВН УВЯЗКА"), (3, "3 ИНТЕРПОЛЯЦИЯ КЕРНА")],
                                   coerce=int, validators=[DataRequired()])
    default_wells = SelectMultipleField('Список доступных скважин', choices=[])
    wells = SelectMultipleField('Список доступных скважин', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Choose')


class ChooseWellsForm(FlaskForm):
    wells = SelectMultipleField('Список доступных скважин', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Choose')


class RunForm(FlaskForm):
    submit = SubmitField('Новый запуск')
