import os
from os import environ

from dotenv import load_dotenv

load_dotenv()

# Secrets MUST come from the environment. The hardcoded placeholders below
# were previously used in production and allowed anyone to forge session
# cookies, password-reset tokens and file-upload JWTs.
SECRET_KEY = environ.get("FLASK_SECRET_KEY") or environ.get("SECRET_KEY")
AUTH_JWT_SECRET_KEY = environ.get("AUTH_JWT_SECRET_KEY")
API_SECRET_TOKEN = environ.get("API_SECRET_TOKEN")

SQLALCHEMY_ENGINES = {
    "default": {
        "url": environ.get("DATABASE_URL"),
    }
}

BABEL_DEFAULT_LOCALE = "en"

SECURITY_PASSWORD_SALT = environ.get("FLASK_SECURITY_PASSWORD_SALT") or environ.get(
    "SECURITY_PASSWORD_SALT"
)
SECURITY_REGISTERABLE = True
SECURITY_SEND_REGISTER_EMAIL = False
SECURITY_CHANGE_EMAIL = True
SECURITY_CHANGEABLE = True
SECURITY_RECOVERABLE = True
SECURITY_TWO_FACTOR = True
SECURITY_TWO_FACTOR_ENABLED_METHODS = ["email", "authenticator"]
SECURITY_TOTP_SECRETS = {1: environ.get("TOTP_SECRET")}
SECURITY_TOTP_ISSUER = "ENRG DocDB"
SECURITY_OAUTH_ENABLE_SLACK = environ.get("FLASK_SECURITY_OAUTH_ENABLE_SLACK", False)
SECURITY_OAUTH_BUILTIN_PROVIDERS = []

SECURITY_POST_LOGIN_VIEW = "index.index"
SECURTIY_POST_LOGOUT_VIEW = "index.index"
SECURITY_POST_REGISTER_VIEW = "index.index"

BOOTSTRAP_BOOTSWATCH_THEME = "pulse"

_upload_folder = environ.get("FILE_UPLOAD_FOLDER", "uploads")
if not os.path.isabs(_upload_folder):
    _upload_folder = os.path.abspath(os.path.join(os.getcwd(), _upload_folder))
FILE_UPLOAD_FOLDER = _upload_folder

FILE_UPLOAD_MAX_FILE_SIZE = 1024 * 1024 * 50
FILE_UPLOAD_TEMP_CLEAR_INTERVAL_HOURS = 4
_temp_folder = environ.get("FILE_UPLOAD_TEMP_FOLDER", "temp_uploads")
if not os.path.isabs(_temp_folder):
    _temp_folder = os.path.abspath(os.path.join(os.getcwd(), _temp_folder))
FILE_UPLOAD_TEMP_FOLDER = _temp_folder

# LDAP Configuration
LDAP_ENABLED = environ.get("LDAP_ENABLED", "false").lower() == "true"
LDAP_PORT = int(environ.get("LDAP_PORT", 10389))
LDAPS_PORT = int(environ.get("LDAPS_PORT", 636))
LDAP_BASE_DN = environ.get("LDAP_BASE_DN", "dc=enrgdocdb")
LDAP_USERS_OU = environ.get("LDAP_USERS_OU", "ou=users")
LDAP_GROUPS_OU = environ.get("LDAP_GROUPS_OU", "ou=groups")
LDAP_ADMIN_PASSWORD = environ.get("LDAP_ADMIN_PASSWORD")

# LDAP TLS/SSL Configuration
LDAP_USE_TLS = environ.get("LDAP_USE_TLS", "false").lower() == "true"
LDAP_TLS_CERT_FILE = environ.get("LDAP_TLS_CERT_FILE")
LDAP_TLS_KEY_FILE = environ.get("LDAP_TLS_KEY_FILE")
LDAP_TLS_CA_FILE = environ.get("LDAP_TLS_CA_FILE")

# LDAP Performance Settings
LDAP_CACHE_ENABLED = environ.get("LDAP_CACHE_ENABLED", "false").lower() == "true"
LDAP_CACHE_TYPE = environ.get("LDAP_CACHE_TYPE", "simple")  # simple, redis
LDAP_CACHE_TIMEOUT = int(environ.get("LDAP_CACHE_TIMEOUT", 300))
LDAP_PAGE_SIZE = int(environ.get("LDAP_PAGE_SIZE", 1000))

# LDAP Logging
LDAP_LOG_LEVEL = environ.get("LDAP_LOG_LEVEL", "INFO").upper()
LDAP_LOG_REQUESTS = environ.get("LDAP_LOG_REQUESTS", "false").lower() == "true"

# LDAP Security
LDAP_REQUIRE_SECURE_BINDS = (
    environ.get("LDAP_REQUIRE_SECURE_BINDS", "false").lower() == "true"
)
LDAP_MAX_CONNECTIONS = int(environ.get("LDAP_MAX_CONNECTIONS", 100))
# Per-client-IP bind failure limiting (online brute-force protection)
LDAP_MAX_BIND_FAILURES = int(environ.get("LDAP_MAX_BIND_FAILURES", 10))
LDAP_BIND_FAILURE_WINDOW_SECONDS = int(
    environ.get("LDAP_BIND_FAILURE_WINDOW_SECONDS", 300)
)

if LDAP_ENABLED and not LDAP_ADMIN_PASSWORD:
    raise ValueError("LDAP_ADMIN_PASSWORD must be set when LDAP_ENABLED is true")

if LDAP_ADMIN_PASSWORD and len(LDAP_ADMIN_PASSWORD) < 12:
    raise ValueError("LDAP_ADMIN_PASSWORD must be at least 12 characters long")

# Fail fast on missing or well-known insecure secret values.
_INSECURE_SECRET_VALUES = {
    "your_secret_key",
    "your-secret-key-here",
    "your_password_salt",
    "your-random-salt-string-here",
    "change-me",
    "changeme",
    "secret",
    "password",
    "devkey",
    "devsecret",
    "devsecret_please_change_this_32chars",
}

if not SECRET_KEY or SECRET_KEY in _INSECURE_SECRET_VALUES or len(SECRET_KEY) < 32:
    raise ValueError(
        "SECRET_KEY must be set via the FLASK_SECRET_KEY environment variable "
        "with a random value of at least 32 characters"
    )

if (
    not SECURITY_PASSWORD_SALT
    or SECURITY_PASSWORD_SALT in _INSECURE_SECRET_VALUES
    or len(SECURITY_PASSWORD_SALT) < 16
):
    raise ValueError(
        "SECURITY_PASSWORD_SALT must be set via the "
        "FLASK_SECURITY_PASSWORD_SALT environment variable with a random "
        "value of at least 16 characters"
    )


# Allowed file extensions for user uploads (lowercase, no leading dot).
FILE_UPLOAD_ALLOWED_EXTENSIONS = {
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "txt",
    "md",
    "csv",
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "zip",
    "ics",
    "odt",
    "ods",
    "odp",
}

# LiveKit (Meet module)

# LiveKit (Meet module)
LIVEKIT_API_KEY = environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = environ.get("LIVEKIT_API_SECRET", "")
LIVEKIT_WS_URL = environ.get("LIVEKIT_WS_URL", "ws://localhost:7880")
