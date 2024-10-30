import os

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user

from database import db
from forms.document import DocumentForm
from models.author import Author
from models.document import (
    Document,
    DocumentAuthor,
    DocumentFile,
    DocumentTopic,
    DocumentType,
)
from models.topic import Topic
from models.user import RolePermission
from settings import FILE_UPLOAD_FOLDER
from utils.pagination import paginate
from utils.security import permission_check, secure_blueprint

blueprint = Blueprint("document", __name__, url_prefix="/documents")
secure_blueprint(blueprint)


@blueprint.route("/view/<int:document_id>")
def view(document_id: int):
    document = db.session.query(Document).get(document_id)
    if not document:
        return abort(404)
    if not permission_check(document, RolePermission.VIEW):
        return abort(403)

    return render_template("docdb/view_document.html", document=document)


@blueprint.route("/view-topic/<int:document_type_id>")
def view_document_type(document_type_id: int):
    document_type = db.session.query(DocumentType).get(document_type_id)
    if not document_type:
        return abort(404)

    documents = paginate(
        db.session.query(Document)
        .join(DocumentType, Document.document_type_id == DocumentType.id)
        .filter(DocumentType.id == document_type_id),
        request,
    )

    return render_template(
        "docdb/view_document_type.html",
        document_type=document_type,
        documents=documents,
    )


@blueprint.route("/download-file/<int:file_id>")
def download_file(file_id: int):
    file = db.session.query(DocumentFile).get(file_id)
    if not file:
        return abort(404)
    if not permission_check(file, RolePermission.VIEW):
        return abort(403)

    if FILE_UPLOAD_FOLDER is None:
        return abort(500)

    return send_from_directory(
        FILE_UPLOAD_FOLDER,
        file.real_file_name,
        download_name=file.file_name,
    )


@blueprint.route("/new", methods=["GET", "POST"])
def new():
    form = DocumentForm()
    form.authors.choices = [
        (author.id, author.name) for author in db.session.query(Author).all()
    ]
    form.topics.choices = [
        (topic.id, topic.name) for topic in db.session.query(Topic).all()
    ]
    form.document_type.choices = [
        (document_type.id, document_type.name)
        for document_type in db.session.query(DocumentType).distinct().all()
    ]
    form.organization.choices = list(
        {
            (organization.id, organization.name)
            for organization in [
                x.organization
                for x in current_user.roles
                if RolePermission.ADD in x.permissions
            ]
        }
    )

    if form.validate_on_submit():
        document = Document(
            title=form.title.data,
            abstract=form.abstract.data,
            user_id=current_user.id,
            document_type_id=form.document_type.data,
            organization_id=form.organization.data,
        )
        db.session.add(document)
        db.session.commit()
        for author_id in form.authors.data:
            document_author = DocumentAuthor(
                document_id=document.id, author_id=author_id
            )
            db.session.add(document_author)
        for topic_id in form.topics.data:
            document_topic = DocumentTopic(document_id=document.id, topic_id=topic_id)
            db.session.add(document_topic)

        for file in request.files.getlist(form.files.name):
            if not file.filename:
                continue
            file_extension = file.filename.split(".")[-1]
            file_name = f"doc_{document.id}"
            file_name_extra = 0

            def get_full_file_name():
                return (
                    file_name
                    + ("" if file_name_extra == 0 else f"-{file_name_extra}")
                    + f".{file_extension}"
                )

            def construct_file_path():
                assert FILE_UPLOAD_FOLDER is not None
                return os.path.join(FILE_UPLOAD_FOLDER, get_full_file_name())

            while os.path.exists(construct_file_path()):
                file_name_extra += 1

            # upload the file
            file.save(construct_file_path())

            document_file = DocumentFile(
                document_id=document.id,
                file_name=file.filename,
                real_file_name=get_full_file_name(),
            )
            db.session.add(document_file)
        db.session.commit()

        flash("Document was uploaded successfully")
        return redirect(url_for("document.view", document_id=document.id))

    return render_template("docdb/new_document.html", form=form)
