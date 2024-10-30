import base64
import os
import secrets
import shutil
from datetime import datetime, timedelta
from glob import glob
from pathlib import Path
from typing import cast

import jwt
from flask import (
    Blueprint,
    abort,
    flash,
    json,
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
from models.user import Organization, RolePermission, User
from settings import FILE_UPLOAD_FOLDER, SECRET_KEY
from utils.pagination import paginate
from utils.security import _is_super_admin, permission_check, secure_blueprint

blueprint = Blueprint("document", __name__, url_prefix="/documents")
secure_blueprint(blueprint)

FILE_UPLOAD_TEMP_FOLDER = os.path.join(FILE_UPLOAD_FOLDER, "temp")


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
    document_tokens = [secrets.token_urlsafe(16) for _ in range(10)]

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
                if RolePermission.ADD in x.permissions and x.organization
            ]
        }
    )
    if _is_super_admin(cast(User, current_user)):
        form.organization.choices = [
            (organization.id, organization.name)
            for organization in db.session.query(Organization).all()
        ]

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

        try:
            file_token = jwt.decode(
                form.file_token.data, SECRET_KEY, algorithms=["HS256"]
            )
        except Exception:
            return abort(410)
        document_tokens = file_token["document_tokens"]
        token_to_file_json = json.loads(form.token_to_file.data)
        for uploaded_token, uploaded_file_name in token_to_file_json.items():
            if uploaded_token not in document_tokens:
                continue
            files_with_uploaded_token = glob(
                os.path.join(FILE_UPLOAD_TEMP_FOLDER, f"*{uploaded_token}*")
            )
            if len(files_with_uploaded_token) != 1:
                continue
            file_path = os.path.join(
                FILE_UPLOAD_TEMP_FOLDER, files_with_uploaded_token[0]
            )
            # skip if file doesn't exist
            if not os.path.exists(file_path):
                continue

            # Move folder out of temp folder
            shutil.move(file_path, FILE_UPLOAD_FOLDER)
            file_path = os.path.basename(file_path)

            document_file = DocumentFile(
                document_id=document.id,
                file_name=os.path.basename(uploaded_file_name),
                real_file_name=os.path.basename(file_path),
            )
            db.session.add(document_file)
        db.session.commit()

        flash("Document was uploaded successfully")
        return redirect(url_for("document.view", document_id=document.id))

    return render_template(
        "docdb/new_document.html",
        form=form,
        file_token=jwt.encode(
            {
                "document_tokens": document_tokens,
                "exp": datetime.now() + timedelta(minutes=30),
            },
            SECRET_KEY,
        ),
        document_tokens=document_tokens,
    )


@blueprint.route("/upload-file", methods=["POST"])
def upload_file():
    data_base64 = request.form.get("file")
    file_name = request.form.get("file_name")
    file_token = request.form.get("file_token")
    document_token = request.form.get("document_token")
    if not data_base64 or not file_name or not file_token:
        return abort(400)
    try:
        file_token = jwt.decode(file_token, SECRET_KEY, algorithms=["HS256"])
    except Exception:
        return abort(410)
    if document_token not in file_token["document_tokens"]:
        return abort(400)

    file_extension = file_name.split(".")[-1]
    save_file_name = f"doc_{document_token}.{file_extension}"
    save_file_path = os.path.join(FILE_UPLOAD_TEMP_FOLDER, save_file_name)

    # Create temp folder if it doesn't exist
    Path(FILE_UPLOAD_TEMP_FOLDER).mkdir(parents=True, exist_ok=True)

    # Create file if it doesn't exist
    Path(save_file_path).touch(exist_ok=True)

    # Append to save_file_path
    with open(save_file_path, "ab") as f:
        f.write(base64.b64decode(data_base64))

    return "OK", 204
