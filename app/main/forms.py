from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, MultipleFileField, BooleanField
from wtforms.validators import ValidationError, DataRequired, Email

from app.models import User


class ProjectForm(FlaskForm):
    name = StringField('Название проекта', validators=[DataRequired()])
    submit = SubmitField('Добавить проект')


class ProjectEditForm(FlaskForm):
    name = StringField('Новое название проекта')
    coords_file = MultipleFileField('Загрузить координаты')
    core_file = MultipleFileField('Загрузить керн')
    logs_file = MultipleFileField('Загрузить кривые')
    strat_file = MultipleFileField('Загрузить стратиграфию')
    surf_top_file = MultipleFileField('Загрузить верхнюю поверхность сетки')
    surf_bot_file = MultipleFileField('Загрузить нижнюю поверхность сетки')
    grid_file = MultipleFileField('Загрузить пустую сетку')
    grid_fes_file = MultipleFileField('Загрузить сетку с показателями')
    unnamed_well = BooleanField('Номер скважины брать из названия файла')

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


