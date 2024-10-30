from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import (
    HiddenField,
    MultipleFileField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired


class DocumentForm(FlaskForm):
    title = StringField("Title", validators=[])
    abstract = TextAreaField("Abstract")
    authors = SelectMultipleField("Authors", coerce=int, choices=[], validators=[])
    topics = SelectMultipleField("Topics", coerce=int, choices=[], validators=[])
    document_type = SelectField(
        "Document Type",
        coerce=int,
        choices=[],
        validators=[
            FileAllowed(["pdf", "doc", "docx", "xls", "xlsx", "mp4", "avi"]),
        ],
    )
    organization = SelectField(
        "Organization",
        coerce=int,
        choices=[],
        validators=[DataRequired()],
    )
    files = MultipleFileField("File(s)")
    token_to_file = HiddenField()
    file_token = HiddenField()
    submit = SubmitField("Submit")
