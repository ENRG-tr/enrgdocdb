from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length

from ..forms.file import FileForm


class WikiPageForm(FileForm, FlaskForm):
    """Form for creating and editing wiki pages."""

    title = StringField("Title", validators=[DataRequired(), Length(max=512)])
    slug = StringField("Slug", validators=[DataRequired(), Length(max=512)])
    content = TextAreaField("Content", validators=[DataRequired()])
    parent_id = SelectField("Parent Page", choices=[], validators=None)
    is_pinned = BooleanField("Pin to top")
    comment = StringField("Revision comment", validators=[Length(max=1024)])
    submit = SubmitField("Save Page")
