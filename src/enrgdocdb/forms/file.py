from wtforms import HiddenField, MultipleFileField


class FileForm:
    files = MultipleFileField("File(s)")
    token_to_file = HiddenField()
    file_token = HiddenField()
