from flask_wtf import FlaskForm
from wtforms import PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Optional

from ..database import db
from ..models.user import Role


class EditUserProfileForm(FlaskForm):
    email = StringField("Email", render_kw={"readonly": True}, validators=[])
    username = StringField("Username", render_kw={"readonly": True}, validators=[])
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    new_password = PasswordField(
        "Set Account Password",
        validators=[Optional()],
    )
    confirm_password = PasswordField(
        "Confirm Account Password",
        validators=[EqualTo("new_password", message="Passwords must match")],
    )
    submit = SubmitField("Submit")


class CreateUserForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            EqualTo(
                "password",
                message="Passwords must match",
            )
        ],
    )
    first_name = StringField("First Name", validators=[DataRequired()])
    last_name = StringField("Last Name", validators=[DataRequired()])
    role = SelectField("Role", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Create User")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        roles = [(role.id, str(role)) for role in db.session.query(Role).all()]
        self.role.choices = roles
