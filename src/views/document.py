from os import abort

from flask import Blueprint, render_template, send_from_directory

from database import db
from models.document import Document, DocumentFile

blueprint = Blueprint("document", __name__, url_prefix="/documents")


@blueprint.route("/view/<int:document_id>")
def view(document_id: int):
    # TODO: Check permissions
    document = db.session.query(Document).get(document_id)
    if not document:
        return abort(404)

    return render_template("docdb/document.html", document=document)


@blueprint.route("/download-file/<int:file_id>")
def download_file(file_id: int):
    # TODO: Check permissions
    file = db.session.query(DocumentFile).get(file_id)
    if not file:
        return abort(404)

    file_path = file.file_name

    return send_from_directory(file_path, file_path, as_attachment=True)
