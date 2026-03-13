import re
import unicodedata
from datetime import datetime
from enum import Enum

from flask_security.models import sqla
from sqlalchemy import ForeignKey, String, event, func, orm
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Model, db


class RolePermission(str, Enum):
    VIEW = "VIEW"
    ADD = "ADD"
    EDIT_SELF = "EDIT_SELF"
    EDIT = "EDIT"
    REMOVE = "REMOVE"
    ADMIN = "ADMIN"


ROLES_PERMISSIONS_BY_ORGANIZATION = {
    "guest": [RolePermission.VIEW],
    "user": [RolePermission.VIEW, RolePermission.EDIT_SELF],
    "moderator": [
        RolePermission.VIEW,
        RolePermission.ADD,
        RolePermission.EDIT_SELF,
        RolePermission.EDIT,
        RolePermission.REMOVE,
    ],
}

ADMIN_PERMISSIONS = [p.value for p in RolePermission]


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
        if self.deleted_at:
            return "Deleted User"
        if self.first_name:
            return f"{self.first_name} {self.last_name or ''}"
        return self.email

    def __repr__(self):
        return self.name

    def get_organizations(self):
        from ..utils.security import _is_super_admin

        if _is_super_admin(self):
            return db.session.query(Organization).all()
        return [
            x.organization
            for x in self.roles
            if RolePermission.EDIT_SELF in x.permissions and x.organization
        ]

    @staticmethod
    def transliterate(text):
        if not text:
            return ""
        text = text.replace("ı", "i")
        nfkd_form = unicodedata.normalize("NFKD", text)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

    def _generate_unique_username(self):
        """Generate a unique username based on first and last name."""

        if not self.first_name or not self.last_name:
            return None

        f_name = self.transliterate(self.first_name.strip().lower())
        l_name = self.transliterate(self.last_name.strip().lower())
        l_name = l_name[:10]

        f_init = re.sub(r"[^a-z0-9]", "", f_name)
        if not f_init:
            f_init = "u"
        f_init = f_init[0]
        l_part = re.sub(r"[^a-z0-9]", "", l_name)

        base_username = f"{f_init}{l_part}"
        if not base_username:
            return None

        # Check for duplicates in the database
        final_username = base_username
        counter = 1

        while True:
            # Check if this username is already taken by ANOTHER user
            existing = (
                db.session.query(User)
                .filter(User.username == final_username, User.id != self.id)
                .first()
            )

            if not existing:
                break

            final_username = f"{base_username}{counter}"
            counter += 1

        return final_username

    def get_ldap_uid(self) -> str:
        """Get LDAP UID. Uses username if set, otherwise falls back to generation."""
        if self.username:
            return self.username

        if hasattr(self, "_cached_ldap_uid"):
            return self._cached_ldap_uid

        f_name = self.transliterate((self.first_name or "").strip().lower())
        l_name = self.transliterate((self.last_name or "").strip().lower())

        if f_name and l_name:
            f_init = re.sub(r"[^a-z0-9]", "", f_name)
            if not f_init:
                f_init = "u"
            f_init = f_init[0]
            l_part = re.sub(r"[^a-z0-9]", "", l_name)
            uid_str = f"{f_init}{l_part}"
        elif f_name:
            uid_str = re.sub(r"[^a-z0-9]", "", f_name)
        else:
            email_part = self.transliterate((self.email or "").split("@")[0].lower())
            uid_str = re.sub(r"[^a-z0-9]", "", email_part)

        if not uid_str:
            uid_str = str(self.id)

        self._cached_ldap_uid = uid_str
        return uid_str


class Organization(Model):
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(512))

    roles: Mapped[list["Role"]] = relationship(back_populates="organization")

    def __repr__(self) -> str:
        return self.name


# Event listeners to automatically generate username
@event.listens_for(User, "before_insert")
@event.listens_for(User, "before_update")
def receive_before_flush(mapper, connection, target):
    if not target.username and target.first_name and target.last_name:
        target.username = target._generate_unique_username()
