from random import random

from flask import render_template, url_for
from markupsafe import Markup
from wtforms import Field


class EditInlineModelField(Field):
    class LinkWidget(object):
        def __call__(self, field, **kwargs):
            return render_template(
                "docdb/snippets/edit_inline_model_field.html",
                random_id=random(),
                edit_view_url=url_for(field.edit_view),
                label=field.label,
            )

    widget = LinkWidget()

    def __init__(self, edit_view: str, **kwargs):
        super(EditInlineModelField, self).__init__(**kwargs)
        self.edit_view = edit_view

    def process(self, formdata, data=None, **kwargs):
        super(EditInlineModelField, self).process(formdata, data)
        self.object_data = data
