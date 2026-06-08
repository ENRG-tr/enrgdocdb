from flask_wtf import FlaskForm
from wtforms import MultipleFileField


class FileForm(FlaskForm):
    files = MultipleFileField("File(s)")
