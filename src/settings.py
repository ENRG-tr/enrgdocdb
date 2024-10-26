SECRET_KEY = "your_secret_key"

SECURITY_PASSWORD_SALT = "your_password_salt"

SQLALCHEMY_ENGINES = {
    "default": {
        "url": "sqlite:///db.sqlite",
    }
}

BABEL_DEFAULT_LOCALE = "tr"
SECURITY_REGISTERABLE = True
SECURITY_SEND_REGISTER_EMAIL = False
