import os
import secrets
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from glob import glob

import jwt
from flask import Request, json


@dataclass
class UserFile:
    file_path: str
    uploaded_file_name: str


@dataclass
class UserFileUploadResult:
    template_args: dict
    user_files: list[UserFile] | None


def handle_user_file_upload(request: Request) -> UserFileUploadResult:
    from settings import FILE_UPLOAD_FOLDER, FILE_UPLOAD_TEMP_FOLDER, SECRET_KEY

    """
    Handles file upload for user.

    This function is used to handle file upload for user. It takes in a request object
    and returns a UserFileUploadResult object. The UserFileUploadResult object contains
    the template arguments and the user files.

    A form that utilizes this function should have:
    - A hidden field called "file_token" that contains a jwt token with the document_tokens
    - A hidden field called "token_to_file" that contains a json string with the token
      to file mapping
    """

    uploaded_file_paths = []

    def _get_result(user_files=None) -> UserFileUploadResult:
        document_tokens = [secrets.token_urlsafe(16) for _ in range(10)]
        return UserFileUploadResult(
            template_args={
                "file_token": jwt.encode(
                    {
                        "document_tokens": document_tokens,
                        "exp": datetime.now() + timedelta(minutes=30),
                    },
                    SECRET_KEY,
                ),
                "document_tokens": document_tokens,
            },
            user_files=user_files,
        )

    if request.method == "POST":
        file_token = request.form.get("file_token")
        if not file_token:
            return _get_result()

        # Try to parse file_token jwt and get document_tokens
        try:
            file_token = jwt.decode(file_token, SECRET_KEY, algorithms=["HS256"])
            document_tokens = file_token["document_tokens"]
        except Exception:
            return _get_result()

        token_to_file = request.form.get("token_to_file")
        if not document_tokens or not token_to_file:
            return _get_result()

        # Try to parse token_to_file json
        try:
            token_to_file_json = json.loads(token_to_file)
        except Exception:
            return _get_result()

        for uploaded_token, uploaded_file_name in token_to_file_json.items():
            if uploaded_token not in document_tokens:
                continue

            # Search for file with uploaded_token in temp folder
            files_with_uploaded_token = glob(
                os.path.join(FILE_UPLOAD_TEMP_FOLDER, f"*{uploaded_token}*")
            )

            # Skip if no file found or more than one file found (which shouldn't happen)
            if len(files_with_uploaded_token) != 1:
                continue

            # Get real file path
            file_path = os.path.join(
                FILE_UPLOAD_TEMP_FOLDER, files_with_uploaded_token[0]
            )

            # Skip if file doesn't exist (which also shouldn't happen)
            if not os.path.exists(file_path):
                continue

            # Move folder out of temp folder to upload folder
            shutil.move(file_path, FILE_UPLOAD_FOLDER)
            file_path = os.path.basename(file_path)
            uploaded_file_paths.append(UserFile(file_path, uploaded_file_name))

        return _get_result(uploaded_file_paths)

    return _get_result()
