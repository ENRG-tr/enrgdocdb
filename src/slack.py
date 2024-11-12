from os import environ

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
        profile = token["userinfo"]
        return "email", profile["email"]
