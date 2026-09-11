import base64
import os
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path

import jwt
from flask import Blueprint, abort, current_app, request, send_from_directory

from ..database import db
from ..models.user import RolePermission
from ..settings import (
    FILE_UPLOAD_MAX_FILE_SIZE,
    FILE_UPLOAD_TEMP_CLEAR_INTERVAL_HOURS,
    FILE_UPLOAD_TEMP_FOLDER,
)
from ..utils.file import get_file_extension, is_allowed_upload_filename
from ..utils.logging import get_logger
from ..utils.security import secure_blueprint

blueprint = Blueprint("file", __name__, url_prefix="/file")
secure_blueprint(blueprint)

logger = get_logger(__name__)

# Tokens are URL-safe base64 strings; restricting the charset prevents path
# tricks via the generated file name even if a token is ever forged.
_DOCUMENT_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# Extensions that are safe to serve inline (images only). Everything else is
# served as a download to prevent active content (HTML/SVG) XSS.
INLINE_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}


last_temp_cleanup_date = datetime.now() - timedelta(
    hours=FILE_UPLOAD_TEMP_CLEAR_INTERVAL_HOURS
)
last_temp_cleanup_date_lock = threading.Lock()


@blueprint.route("/upload-file", methods=["POST"])
def upload_file():
    data_base64 = request.form.get("file")
    file_name = request.form.get("file_name")
    file_token = request.form.get("file_token")
    document_token = request.form.get("document_token")
    if not data_base64 or not file_name or not file_token or not document_token:
        return abort(400)
    if not _DOCUMENT_TOKEN_RE.match(document_token):
        return abort(400)
    if not is_allowed_upload_filename(file_name):
        logger.warning(f"Rejected upload with disallowed extension: {file_name}")
        return abort(400)
    if (
        request.content_length
        and request.content_length > FILE_UPLOAD_MAX_FILE_SIZE + 1024 * 1024
    ):
        return abort(413)
    try:
        file_token = jwt.decode(
            file_token, current_app.config["SECRET_KEY"], algorithms=["HS256"]
        )
    except Exception:
        return abort(410)
    if document_token not in file_token["document_tokens"]:
        return abort(400)

    file_extension = get_file_extension(file_name)
    save_file_name = f"doc_{document_token}.{file_extension}"
    save_file_path = os.path.join(FILE_UPLOAD_TEMP_FOLDER, save_file_name)

    # Create temp folder if it doesn't exist
    Path(FILE_UPLOAD_TEMP_FOLDER).mkdir(parents=True, exist_ok=True)

    # Create file if it doesn't exist
    Path(save_file_path).touch(exist_ok=True)

    # Append to save_file_path
    with open(save_file_path, "ab") as f:
        f.write(base64.b64decode(data_base64))
    file_size = os.path.getsize(save_file_path)

    # Check if file size is greater than max file size
    if file_size > FILE_UPLOAD_MAX_FILE_SIZE:
        os.remove(save_file_path)
        return abort(413)

    threading.Thread(target=_cleanup_temp_folder).start()

    return "OK", 204


@blueprint.route("/get/<filename>")
def get_file(filename):
    """Serve a stored upload, but only after DB-backed authorization."""
    from ..models.document import DocumentFile
    from ..models.wiki import WikiFile
    from ..settings import FILE_UPLOAD_FOLDER
    from ..utils import security as security_utils

    # Only serve files that are registered in the database. This prevents
    # access to orphaned/temp files and files of deleted records.
    file_record = db.session.query(DocumentFile).filter_by(
        real_file_name=filename
    ).first()
    if file_record is None:
        file_record = (
            db.session.query(WikiFile).filter_by(real_file_name=filename).first()
        )
    if file_record is None:
        return abort(404)

    if not security_utils.permission_check(file_record, RolePermission.VIEW):
        return abort(403)

    if not FILE_UPLOAD_FOLDER or not os.path.exists(
        os.path.join(FILE_UPLOAD_FOLDER, filename)
    ):
        return abort(404)

    # Images are served inline (safe, allowlisted types); everything else is
    # forced to download so attacker content can never render on our origin.
    as_attachment = get_file_extension(filename) not in INLINE_IMAGE_EXTENSIONS
    response = send_from_directory(
        FILE_UPLOAD_FOLDER,
        filename,
        download_name=file_record.file_name,
        as_attachment=as_attachment,
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def _cleanup_temp_folder():
    global last_temp_cleanup_date, last_temp_cleanup_date_lock
    with last_temp_cleanup_date_lock:
        interval_threshold = datetime.now() - timedelta(
            hours=FILE_UPLOAD_TEMP_CLEAR_INTERVAL_HOURS
        )
        if last_temp_cleanup_date > interval_threshold:
            return

        for file in os.listdir(FILE_UPLOAD_TEMP_FOLDER):
            file_path = os.path.join(FILE_UPLOAD_TEMP_FOLDER, file)
            file_modification_time = os.path.getmtime(file_path)
            if not file_modification_time:
                continue
            file_modification_time = datetime.fromtimestamp(file_modification_time)
            # Delete files older than 4 hour
            if file_modification_time < interval_threshold:
                os.remove(file_path)
        last_temp_cleanup_date = datetime.now()
