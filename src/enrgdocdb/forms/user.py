from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Optional


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
