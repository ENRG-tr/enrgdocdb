from os import environ

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = "your_secret_key"

SQLALCHEMY_ENGINES = {
    "default": {
        "url": environ.get("DATABASE_URL"),
    }
}

BABEL_DEFAULT_LOCALE = "en"

SECURITY_PASSWORD_SALT = "your_password_salt"
SECURITY_REGISTERABLE = True
SECURITY_SEND_REGISTER_EMAIL = False
SECURITY_CHANGE_EMAIL = True
SECURITY_CHANGEABLE = True
SECURITY_RECOVERABLE = True
SECURITY_TWO_FACTOR = True
SECURITY_TWO_FACTOR_ENABLED_METHODS = ["email", "authenticator"]
SECURITY_TOTP_SECRETS = {1: environ.get("TOTP_SECRET")}
SECURITY_TOTP_ISSUER = "ENRG DocDB"

BOOTSTRAP_BOOTSWATCH_THEME = "pulse"
