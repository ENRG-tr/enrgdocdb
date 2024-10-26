from flask_security.models import sqla as sqla

from database import Model


class Role(Model, sqla.FsRoleMixin):
    __tablename__ = "role"


class User(Model, sqla.FsUserMixin):
    __tablename__ = "user"
