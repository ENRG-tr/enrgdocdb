import logging
import re
from typing import TYPE_CHECKING, Any

import requests

from ..settings import LLDAP_ADMIN_PASSWORD, LLDAP_ADMIN_USER, LLDAP_URL

if TYPE_CHECKING:
    from ..models.user import User

logger = logging.getLogger(__name__)


# LDAP uids can't contain @ or dots
_UID_UNSAFE = re.compile(r"[^a-z0-9_\-]")


def _email_to_uid(email: str) -> str:
    """john.doe@example.com → john_doe_at_example_com"""
    local, _, domain = email.partition("@")
    return _UID_UNSAFE.sub("_", f"{local}_at_{domain}".lower())


def _role_to_group_name(role) -> str:
    """user @ Physics Lab → user_physics_lab, admin @ None → admin_global"""
    org_slug = (
        _UID_UNSAFE.sub("_", role.organization.name.lower())
        if role.organization
        else "global"
    )
    return f"{role.name}_{org_slug}"


def is_enabled() -> bool:
    return bool(LLDAP_URL and LLDAP_ADMIN_PASSWORD)


# Internal helpers


def _get_token() -> str:
    resp = requests.post(
        f"{LLDAP_URL}/auth/simple/login",
        json={"username": LLDAP_ADMIN_USER, "password": LLDAP_ADMIN_PASSWORD},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def _graphql(query: str, variables: dict | None = None) -> dict:
    token = _get_token()
    resp = requests.post(
        f"{LLDAP_URL}/api/graphql",
        json={"query": query, "variables": variables or {}},
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"LLDAP GraphQL error: {data['errors']}")
    return data["data"]


# User operations


def _lldap_create_user(uid: str, user: "User") -> None:
    _graphql(
        """
        mutation CreateUser($user: CreateUserInput!) {
            createUser(user: $user) { id }
        }
        """,
        {
            "user": {
                "id": uid,
                "email": user.email,
                "displayName": user.name,
                "firstName": user.first_name or "",
                "lastName": user.last_name or "",
            }
        },
    )


def _lldap_update_user(uid: str, user: "User") -> None:
    _graphql(
        """
        mutation UpdateUser($user: UpdateUserInput!) {
            updateUser(user: $user) { ok }
        }
        """,
        {
            "user": {
                "id": uid,
                "email": user.email,
                "displayName": user.name,
                "firstName": user.first_name or "",
                "lastName": user.last_name or "",
            }
        },
    )


def _lldap_delete_user(uid: str) -> None:
    _graphql(
        """
        mutation DeleteUser($userId: String!) {
            deleteUser(userId: $userId) { ok }
        }
        """,
        {"userId": uid},
    )


# Group operations


def _lldap_get_all_groups() -> dict[str, int]:
    data = _graphql("{ groups { id displayName } }")
    return {g["displayName"]: g["id"] for g in data["groups"]}


def _lldap_ensure_group(name: str, existing: dict[str, int]) -> int:
    """Create group if missing, return its id."""
    if name in existing:
        return existing[name]
    data = _graphql(
        """
        mutation CreateGroup($name: String!) {
            createGroup(name: $name) { id }
        }
        """,
        {"name": name},
    )
    gid = data["createGroup"]["id"]
    existing[name] = gid
    logger.info(f"LLDAP: Created group '{name}' (id={gid})")
    return gid


def _lldap_set_user_groups(
    uid: str, desired_group_ids: set[int], existing_groups: dict[str, int]
) -> None:
    for gid in desired_group_ids:
        _graphql(
            """
            mutation AddUserToGroup($userId: String!, $groupId: Int!) {
                addUserToGroup(userId: $userId, groupId: $groupId) { ok }
            }
            """,
            {"userId": uid, "groupId": gid},
        )


# Public API


def sync_user(user: "User") -> None:
    """Upsert user in LLDAP and sync their group memberships.

    Each DocDB role maps to one LLDAP group (e.g. user_physics_lab).
    No-op when LLDAP is not configured.
    """
    if not is_enabled():
        logger.debug("LLDAP not configured — skipping sync for %s", user.email)
        return

    if user.deleted_at:
        remove_user(user)
        return

    uid = _email_to_uid(user.email)
    try:
        _lldap_create_user(uid, user)
        logger.info("LLDAP: Created user %s (%s)", uid, user.email)
    except RuntimeError:
        # User already exists — update profile fields
        try:
            _lldap_update_user(uid, user)
            logger.info("LLDAP: Updated user %s (%s)", uid, user.email)
        except Exception as e:
            logger.warning("LLDAP: Could not update user %s: %s", uid, e)

    if not user.roles:
        return

    try:
        existing_groups = _lldap_get_all_groups()
        desired_ids: set[int] = set()
        for role in user.roles:
            gid = _lldap_ensure_group(_role_to_group_name(role), existing_groups)
            desired_ids.add(gid)
        _lldap_set_user_groups(uid, desired_ids, existing_groups)
    except Exception as e:
        logger.warning("LLDAP: Group sync failed for %s: %s", uid, e)


def init_app(app: Any) -> None:
    """Register signal hooks and CLI command. No-op when LLDAP is not configured."""
    if not is_enabled():
        logger.debug("LLDAP not configured — integration disabled")
        return

    logger.info("LLDAP integration enabled — syncing to %s", LLDAP_URL)

    from flask_security.signals import password_changed, user_registered

    @user_registered.connect_via(app)
    def on_user_registered(sender, user, **extra):
        try:
            sync_user(user)
        except Exception as exc:
            logger.error(
                "LLDAP sync failed on registration for %s: %s", user.email, exc
            )

    @password_changed.connect_via(app)
    def on_password_changed(sender, user, **extra):
        try:
            sync_user(user)
        except Exception as exc:
            logger.error(
                "LLDAP sync failed on password change for %s: %s", user.email, exc
            )

    import click

    @app.cli.command("lldap-sync")
    @click.option(
        "--dry-run", is_flag=True, default=False, help="Preview without making changes."
    )
    def lldap_sync_command(dry_run: bool) -> None:
        """Sync all active DocDB users to LLDAP.

        \b
        Usage:
          uv run flask lldap-sync
          uv run flask lldap-sync --dry-run
        """
        from ..database import db
        from ..models.user import User

        users = (
            db.session.query(User)
            .filter(User.active.is_(True), User.deleted_at.is_(None))
            .all()
        )

        click.echo(f"Found {len(users)} active user(s) to sync.")
        if dry_run:
            click.echo("[dry-run] No changes will be made.")

        ok = failed = 0
        for user in users:
            if dry_run:
                roles = (
                    ", ".join(_role_to_group_name(r) for r in user.roles)
                    or "(no roles)"
                )
                click.echo(f"  [dry-run] {user.email}  →  groups: {roles}")
                continue
            try:
                sync_user(user)
                click.echo(f"  ✓  {user.email}")
                ok += 1
            except Exception as exc:
                click.echo(f"  ✗  {user.email}: {exc}", err=True)
                failed += 1

        if not dry_run:
            click.echo(f"\nDone: {ok} synced, {failed} failed.")


def remove_user(user: "User") -> None:
    """Remove user from LLDAP. No-op when LLDAP is not configured."""
    if not is_enabled():
        logger.debug("LLDAP not configured — skipping removal for %s", user.email)
        return

    uid = _email_to_uid(user.email)
    try:
        _lldap_delete_user(uid)
        logger.info("LLDAP: Deleted user %s (%s)", uid, user.email)
    except Exception as e:
        logger.warning("LLDAP: Could not delete user %s: %s", uid, e)


def update_password(user: "User", new_plaintext_password: str) -> None:
    """Update user's password in LLDAP. No-op when LLDAP is not configured."""
    if not is_enabled():
        logger.debug(
            "LLDAP not configured — skipping password update for %s", user.email
        )
        return

    uid = _email_to_uid(user.email)
    try:
        _graphql(
            """
            mutation ChangePasswordByAdmin($userId: String!, $password: String!) {
                changeUserPassword(userId: $userId, password: $password) { ok }
            }
            """,
            {"userId": uid, "password": new_plaintext_password},
        )
        logger.info("LLDAP: Updated password for user %s", uid)
    except Exception as e:
        logger.warning("LLDAP: Could not update password for %s: %s", uid, e)
