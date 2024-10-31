import base64
import os
import threading
from datetime import datetime, timedelta
from pathlib import Path

import jwt
from flask import Blueprint, abort, request

from settings import (
    FILE_UPLOAD_MAX_FILE_SIZE,
    FILE_UPLOAD_TEMP_CLEAR_INTERVAL_HOURS,
    FILE_UPLOAD_TEMP_FOLDER,
    SECRET_KEY,
)
from utils.security import secure_blueprint

blueprint = Blueprint("file", __name__, url_prefix="/file")
secure_blueprint(blueprint)


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
    file_size = os.path.getsize(save_file_path)

    # Check if file size is greater than max file size
    if file_size > FILE_UPLOAD_MAX_FILE_SIZE:
        os.remove(save_file_path)
        return abort(413)

    threading.Thread(target=_cleanup_temp_folder).start()

    return "OK", 204


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
