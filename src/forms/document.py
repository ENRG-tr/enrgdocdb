from flask_wtf import FlaskForm
from wtforms import (
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired

from forms.file import FileForm


class DocumentForm(FileForm, FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    abstract = TextAreaField("Abstract")
    authors = SelectMultipleField(
        "Authors", coerce=int, choices=[], validators=[DataRequired()]
    )
    topics = SelectMultipleField(
        "Topics", coerce=int, choices=[], validators=[DataRequired()]
    )
    document_type = SelectField(
        "Document Type",
        coerce=int,
        choices=[],
        validators=[DataRequired()],
    )
    organization = SelectField(
        "Organization",
        coerce=int,
        choices=[],
        validators=[DataRequired()],
    )
    submit = SubmitField("Submit")
