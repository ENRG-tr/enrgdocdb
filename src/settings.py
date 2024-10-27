SECRET_KEY = "your_secret_key"

SECURITY_PASSWORD_SALT = "your_password_salt"

SQLALCHEMY_ENGINES = {
    "default": {
        "url": "sqlite:///db.sqlite",
    }
}

BABEL_DEFAULT_LOCALE = "en"

SECURITY_REGISTERABLE = True
SECURITY_SEND_REGISTER_EMAIL = False
SECURITY_CHANGE_EMAIL = True
SECURITY_TWO_FACTOR = True
SECURITY_TWO_FACTOR_ENABLED_METHODS = ["email", "authenticator"]
SECURITY_TOTP_SECRETS = {1: "your_secret_key"}
SECURITY_TOTP_ISSUER = "ENRG DocDB"

BOOTSTRAP_BOOTSWATCH_THEME = "pulse"
