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

from ..database import db
from ..utils.logging import get_logger

from ..forms.document import DocumentForm, DocumentUploadFilesForm
from ..models.author import Author
from ..models.document import (
    Document,
    DocumentAuthor,
    DocumentFile,
    DocumentTopic,
    DocumentType,
)
from ..models.event import TalkNote
from ..models.topic import Topic
from ..models.user import RolePermission
from ..settings import FILE_UPLOAD_FOLDER
from ..utils import security
from ..utils.file import handle_user_file_upload
from ..utils.pagination import paginate

blueprint = Blueprint("document", __name__, url_prefix="/documents")
security.secure_blueprint(blueprint)

logger = get_logger(__name__)


@blueprint.route("/view/<int:document_id>")
def view(document_id: int):
    logger.debug(f"Viewing document {document_id}")
    document = db.session.query(Document).get(document_id)
    if not document:
        logger.warning(f"Document {document_id} not found")
        return abort(404)
    if not security.permission_check(document, RolePermission.VIEW):
        logger.warning(
            f"Permission denied: user {getattr(current_user, 'id', 'anonymous')} tried to view document {document_id}"
        )
        return abort(403)
    logger.info(
        f"Document {document_id} viewed by user {getattr(current_user, 'id', 'anonymous')}"
    )
    return render_template("docdb/view_document.html", document=document)


@blueprint.route("/view-topic/<int:document_type_id>")
def view_document_type(document_type_id: int):
    logger.debug(f"Viewing document type {document_type_id}")
    document_type = db.session.query(DocumentType).get(document_type_id)
    if not document_type:
        logger.warning(f"Document type {document_type_id} not found")
        return abort(404)

    documents = paginate(
        db.session.query(Document)
        .join(DocumentType, Document.document_type_id == DocumentType.id)
        .filter(DocumentType.id == document_type_id),
        request,
    )

    logger.info(
        f"Document type {document_type_id} viewed: {documents.total_count} documents"
    )
    return render_template(
        "docdb/view_document_type.html",
        document_type=document_type,
        documents=documents,
    )


@blueprint.route("/download-file/<int:file_id>")
def download_file(file_id: int):
    logger.debug(f"Downloading file {file_id}")
    file = db.session.query(DocumentFile).get(file_id)
    if not file:
        logger.warning(f"File {file_id} not found")
        return abort(404)
    if not security.permission_check(file, RolePermission.VIEW):
        logger.warning(
            f"Permission denied: user {getattr(current_user, 'id', 'anonymous')} tried to download file {file_id}"
        )
        return abort(403)

    if FILE_UPLOAD_FOLDER is None:
        logger.error(f"File upload folder not configured for file {file_id}")
        return abort(500)

    logger.info(
        f"File {file.file_name} downloaded by user {getattr(current_user, 'id', 'anonymous')}"
    )
    return send_from_directory(
        FILE_UPLOAD_FOLDER,
        file.real_file_name,
        download_name=file.file_name,
    )


@blueprint.route("/new", methods=["GET", "POST"])
def new():
    if not security.permission_check(None, RolePermission.ADD):
        logger.warning(
            f"Permission denied: user {getattr(current_user, 'id', 'anonymous')} tried to create new document"
        )
        return abort(403)

    """
    Create a new document.

    form_token and document_tokens are a new addition by me, and what we're trying to
    accomplish with these hidious hacks is to allow user to upload multiple files
    with base64 to avoid some firewall issues of a particular web hosting service.

    (Also without adding anything to the database, which would be easier, but yeah.)

    The idea is to generate a set of tokens, and allow the user to associate each token
    with a file. Then, when the user submits the form, we can check if the token is
    associated with a file, and if so, move the file to the right place and associate
    it with the document.
    """
    form = DocumentForm()
    form.authors.choices = [
        (author.id, str(author)) for author in db.session.query(Author).all()
    ]
    form.topics.choices = [
        (topic.id, str(topic)) for topic in db.session.query(Topic).all()
    ]
    form.document_type.choices = [
        (document_type.id, document_type.name)
        for document_type in db.session.query(DocumentType).distinct().all()
    ]
    form.organization.choices = list(
        {
            (organization.id, organization.name)
            for organization in (
                current_user.get_organizations()
                if current_user.is_authenticated
                else []
            )
        }
    )

    user_files_result = handle_user_file_upload(request)
    url = request.args.get("url")

    if form.validate_on_submit():
        logger.info(
            f"Creating new document by user {getattr(current_user, 'id', 'anonymous')}"
        )
        document = Document(
            title=form.title.data,
            abstract=form.abstract.data,
            user_id=getattr(current_user, "id", None),
            document_type_id=form.document_type.data,
            organization_id=form.organization.data,
        )
        db.session.add(document)
        # Commit document in order to get the document id
        db.session.commit()

        # Attach talk note to document if requested
        attach_talk_note_id = request.args.get("attach_talk_note_id")
        if attach_talk_note_id:
            talk_note = db.session.query(TalkNote).get(attach_talk_note_id)
            if talk_note.document_id:
                flash("Talk note already has an attached document.", "error")
                logger.warning(
                    f"Talk note {attach_talk_note_id} already has document attached"
                )
            else:
                talk_note.document_id = document.id
                logger.info(
                    f"Attached talk note {attach_talk_note_id} to document {document.id}"
                )

        for author_id in form.authors.data:
            document_author = DocumentAuthor(
                document_id=document.id, author_id=author_id
            )
            db.session.add(document_author)
        for topic_id in form.topics.data:
            document_topic = DocumentTopic(document_id=document.id, topic_id=topic_id)
            db.session.add(document_topic)

        # Handle user files
        if user_files_result.user_files:
            logger.info(
                f"Uploading {len(user_files_result.user_files)} files to document {document.id}"
            )
            for user_file in user_files_result.user_files:
                document_file = DocumentFile(
                    document_id=document.id,
                    file_name=user_file.uploaded_file_name,
                    real_file_name=user_file.file_path,
                )
                db.session.add(document_file)
        db.session.commit()

        logger.info(
            f"Document {document.id} created successfully by user {getattr(current_user, 'id', 'anonymous')}"
        )
        flash("Document was uploaded successfully!", "success")
        if not url:
            url = url_for("document.view", document_id=document.id)
        return redirect(url)

    return render_template(
        "docdb/new_document.html",
        form=form,
        user_files=user_files_result.template_args,
    )


@blueprint.route("/upload_files", methods=["GET", "POST"])
def upload_files():
    document_id = request.args.get("id")
    redirect_url = request.args.get("url")
    if not document_id:
        return abort(404)
    document = db.session.query(Document).get(document_id)
    if not document:
        return abort(404)
    if not security.permission_check(document, RolePermission.EDIT):
        logger.warning(
            f"Permission denied: user {getattr(current_user, 'id', 'anonymous')} tried to upload files to document {document_id}"
        )
        return abort(403)

    form = DocumentUploadFilesForm()
    user_files_result = handle_user_file_upload(request)

    if form.validate_on_submit():
        logger.info(
            f"Uploading {len(user_files_result.user_files)} files to document {document.id} by user {getattr(current_user, 'id', 'anonymous')}"
        )
        for user_file in user_files_result.user_files:
            document_file = DocumentFile(
                document_id=document.id,
                file_name=user_file.uploaded_file_name,
                real_file_name=user_file.file_path,
            )
            db.session.add(document_file)
        db.session.commit()

        logger.info(f"Files uploaded successfully to document {document.id}")
        flash("Files were uploaded successfully!", "success")
        if not redirect_url:
            return redirect(url_for("document.view", document_id=document.id))
        return redirect(redirect_url)

    return render_template(
        "docdb/document_upload_files.html",
        form=form,
        user_files=user_files_result.template_args,
        document=document,
    )


@blueprint.route("/delete-file/<int:file_id>")
def delete_file(file_id: int):
    file = db.session.query(DocumentFile).get(file_id)
    if not file:
        logger.warning(f"Document file {file_id} not found")
        return abort(404)

    if not security.permission_check(file, RolePermission.EDIT):
        logger.warning(
            f"Permission denied: user {getattr(current_user, 'id', 'anonymous')} tried to delete document file {file_id}"
        )
        return abort(403)

    document_id = file.document_id
    db.session.delete(file)
    db.session.commit()

    logger.info(
        f"Document file {file_id} deleted by user {getattr(current_user, 'id', 'anonymous')}"
    )
    flash("File was deleted successfully", "success")
    return redirect(url_for("document.view", document_id=document_id))
