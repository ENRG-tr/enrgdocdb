from random import random

from flask import render_template, url_for
from markupsafe import Markup
from wtforms import Field, TextAreaField


class EditInlineModelField(Field):
    class LinkWidget:
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
        super().__init__(**kwargs)
        self.edit_view = edit_view
        self.fas_custom_class = fas_custom_class

    def process(self, formdata, data=None, **kwargs):
        super().process(formdata, data)
        self.object_data = data


class RichTextField(TextAreaField):
    def __call__(self, **kwargs):
        id_val = str(kwargs.get("id", f"rich-text-{random()}"))
        kwargs["id"] = id_val
        kwargs["style"] = "display:none;"
        html = super().__call__(**kwargs)

        container_id = id_val + "-quill"
        preview_id = id_val + "-preview"
        editor_html = f"""
        <div id="{container_id}" style="height: 500px; background: #fff;" class="border rounded-bottom"></div>
        <div class="mt-2">
            <input type="file" id="{id_val}-files" multiple style="display:none;">
            <div id="{preview_id}" class="d-flex flex-wrap gap-2"></div>
        </div>
        """

        script_template = """
<script>
    document.addEventListener('DOMContentLoaded', function() {
        var toolbarOptions = [
            ['bold', 'italic', 'underline', 'strike'],
            ['code-block', 'blockquote'],
            [{ 'header': 1 }, { 'header': 2 }],
            [{ 'list': 'ordered'}, { 'list': 'bullet' }],
            ['link', 'image'],
            ['clean']
        ];
        var quill = new Quill('#{{CONTAINER_ID}}', {
            theme: 'snow',
            modules: { toolbar: toolbarOptions }
        });
        var textarea = document.getElementById('{{TEXTAREA_ID}}');
        if (textarea && textarea.value) {
            quill.root.innerHTML = textarea.value;
        }
        quill.on('text-change', function() {
            textarea.value = quill.root.innerHTML;
        });

        // Image handler
        var toolbar = quill.getModule('toolbar');
        toolbar.addHandler('image', function() {
            document.getElementById('{{TEXTAREA_ID}}-files').click();
        });

        // Insert helper
        window.insertInto_{{TEXTAREA_ID}} = function(token, filename) {
            var range = quill.getSelection(true);
            var ext = filename.split('.').pop().toLowerCase();
            var isImage = ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(ext);
            var url = '/file/get/doc_' + token + '.' + ext;
            if (isImage) {
                quill.insertEmbed(range.index, 'image', url);
            } else {
                quill.insertText(range.index, filename, 'link', url);
            }
        };

        // Poll for new files if the form supports them
        var preview = document.getElementById('{{PREVIEW_ID}}');
        var tokenInput = document.querySelector('input[name="token_to_file"]');
        if (tokenInput) {
            var lastMap = "";
            setInterval(function() {
                var mapStr = tokenInput.value;
                if (mapStr === lastMap) return;
                lastMap = mapStr;
                var map = JSON.parse(mapStr);
                preview.innerHTML = '';
                Object.keys(map).forEach(function(token) {
                    var filename = map[token];
                    var btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'btn btn-sm btn-outline-info';
                    btn.innerText = 'Insert ' + filename;
                    btn.onclick = function() { window.insertInto_{{TEXTAREA_ID}}(token, filename); };
                    preview.appendChild(btn);
                });
            }, 1000);
        }
    });
</script>
        """
        script = (
            script_template.replace("{{CONTAINER_ID}}", container_id)
            .replace("{{TEXTAREA_ID}}", id_val)
            .replace("{{PREVIEW_ID}}", preview_id)
        )
        return Markup(html + editor_html + script)
