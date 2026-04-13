from flask_wtf import FlaskForm
from wtforms import HiddenField, MultipleFileField


class FileForm(FlaskForm):
    files = MultipleFileField("File(s)")
    token_to_file = HiddenField()
    file_token = HiddenField()
