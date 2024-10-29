from datetime import datetime
from enum import Enum

from flask_security.models import sqla as sqla
from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Model
from models.base import Base


class RolePermission(str, Enum):
    view = "VIEW"
    add = "ADD"
    edit_self = "EDIT_SELF"
    edit = "EDIT"
    remove = "REMOVE"


ROLES_PERMISSIONS = {
    "user": [RolePermission.view, RolePermission.add, RolePermission.edit_self],
    "admin": [
        RolePermission.view,
        RolePermission.add,
        RolePermission.edit_self,
        RolePermission.edit,
        RolePermission.remove,
    ],
}


class Role(Model, sqla.FsRoleMixin):
    __tablename__ = "role"

    organization_id: Mapped[int | None] = mapped_column(ForeignKey("organizations.id"))
    organization: Mapped["Organization | None"] = relationship(
        "Organization", back_populates="roles"
    )

    update_datetime: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )

    def __repr__(self) -> str:
        if self.organization:
            return f"{self.name.capitalize()} ({self.organization.name})"
        return self.name.capitalize()


class User(Model, sqla.FsUserMixin):
    __tablename__ = "user"
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))

    create_datetime: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp()
    )
    update_datetime: Mapped[datetime] = mapped_column(
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )
    deleted_at: Mapped[datetime | None] = mapped_column()

    @property
    def name(self):
        if self.first_name:
            return f"{self.first_name} {self.last_name or ''}"
        return self.email


class Organization(Base, Model):
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(512))

    roles: Mapped[list[Role]] = relationship()

    def __repr__(self) -> str:
        return self.name
