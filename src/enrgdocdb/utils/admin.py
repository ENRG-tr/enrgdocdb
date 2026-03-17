from random import random

from flask import render_template, url_for
from markupsafe import Markup
from wtforms import Field, TextAreaField


class EditInlineModelField(Field):
    class LinkWidget(object):
        def __call__(self, field, **kwargs):
            return Markup(
                render_template(
                    "docdb/snippets/edit_inline_model_field.html",
                    random_id=random(),
                    edit_view_url=url_for(field.edit_view),
                    label=field.label,
                    fas_custom_class=field.fas_custom_class,
                )
            )

    widget = LinkWidget()

    def __init__(self, edit_view: str, fas_custom_class: str | None = None, **kwargs):
        super(EditInlineModelField, self).__init__(**kwargs)
        self.edit_view = edit_view
        self.fas_custom_class = fas_custom_class

    def process(self, formdata, data=None, **kwargs):
        super(EditInlineModelField, self).process(formdata, data)
        self.object_data = data


class RichTextField(TextAreaField):
    def __call__(self, **kwargs):
        kwargs.setdefault("class", "ck-editor-target")
        html = super().__call__(**kwargs)
        script = """
<script>
    ClassicEditor
        .create(document.querySelector('.ck-editor-target'))
        .catch(error => { console.error(error); });
</script>
        """
        return Markup(html + script)
