from flask_security.models import sqla as sqla
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from database import Model


class Role(Model, sqla.FsRoleMixin):
    __tablename__ = "role"


class User(Model, sqla.FsUserMixin):
    __tablename__ = "user"
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
