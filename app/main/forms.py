from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, FileField, MultipleFileField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo
from app.models import User



class ProjectForm(FlaskForm):
    name = StringField('Project name', validators=[DataRequired()])
    submit = SubmitField('Add project')


class ProjectEditForm(FlaskForm):
    name = StringField('Rename your project')
    coords_file = MultipleFileField('Coords File')
    core_file = MultipleFileField('Core File')
    logs_file = MultipleFileField('Logs File')
    submit = SubmitField('Edit project')



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