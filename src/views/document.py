from flask import Blueprint, abort, render_template, send_from_directory

from database import db
from models.document import Document, DocumentFile
from settings import FILE_UPLOAD_FOLDER

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

    return send_from_directory(
        FILE_UPLOAD_FOLDER,
        file.real_file_name,
        as_attachment=True,
        download_name=file.file_name,
    )
