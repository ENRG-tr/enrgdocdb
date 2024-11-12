from os import environ
from secrets import token_urlsafe

from argon2 import hash_password
from flask import after_this_request
from flask_security.datastore import UserDatastore
from flask_security.oauth_provider import FsOAuthProvider


def normalize_userinfo(client, data):
    user = data["user"]

    picture = None
    for s in ["512", "192", "72", "48", "32", "24"]:
        src = user.get("image_" + s)
        if src:
            picture = src
            break

    params = {
        "sub": user["id"],
        "email": user["email"],
        "name": user["name"],
    }
    if picture:
        params["picture"] = picture
    return params


def _monkeypatch_user_datastore_for_oauth(user_datastore: UserDatastore, email: str):
    org_find_user = user_datastore.find_user

    def restore_datastore(response=None):
        user_datastore.find_user = org_find_user
        return response

    def find_user(*args, **kwargs):
        user = org_find_user(*args, **kwargs)
        if user is None and email == kwargs.get("email"):
            user = user_datastore.create_user(
                email=email, password=hash_password(token_urlsafe().encode())
            )
        return user

    user_datastore.find_user = find_user

    return restore_datastore


class SlackFsOauthProvider(FsOAuthProvider):
    def authlib_config(self):
        return {
            "client_id": environ.get("FLASK_SLACK_CLIENT_ID"),
            "api_base_url": "https://slack.com/api/",
            "access_token_url": "https://slack.com/api/oauth.access",
            "authorize_url": "https://slack.com/oauth/authorize",
            "client_kwargs": {
                "token_endpoint_auth_method": "client_secret_post",
                "scope": "identity.basic identity.avatar identity.email",
            },
            "userinfo_endpoint": "users.identity",
            "userinfo_compliance_fix": normalize_userinfo,
        }

    def fetch_identity_cb(self, oauth, token):  # pragma no cover
        from app import user_datastore

        profile = token["user"]
        email = profile["email"]
        after_this_request(_monkeypatch_user_datastore_for_oauth(user_datastore, email))
        return "email", profile["email"]
