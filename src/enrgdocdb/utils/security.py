from typing import Any

from flask import Blueprint, current_app, flash, redirect, request, url_for
from flask_limiter import RateLimitExceeded
from flask_login import current_user

from ..app import limiter
from ..database import db
from ..models.author import Author
from ..models.document import Document
from ..models.user import RolePermission, User
from ..models.wiki import WikiPage

RATELIMIT_NON_VIEW_ACTIONS = "180/minute"


def secure_blueprint(blueprint: Blueprint):
    @blueprint.before_request
    def ensure_user_logged_in():
        # Skip authentication check in test mode if desired, but we've enabled it
        if not current_user.is_authenticated:
            # Skip for icalendar routes which use token-based auth
            if request.endpoint and "icalendar" in request.endpoint:
                return None
            # Trigger the unauthorized handler (usually redirect to login)
            return current_app.login_manager.unauthorized()

    @blueprint.before_request
    def ensure_user_has_roles():
        # Only check roles for authenticated users
        if not current_user.is_authenticated:
            return None

        # Check if the user has any roles assigned
        # AnonymousUser won't have the 'roles' attribute from our model
        roles = getattr(current_user, "roles", [])
        if not len(roles) and request.endpoint != "index.no_role":
            return redirect(url_for("index.no_role"))

    @blueprint.before_request
    def ensure_user_has_filled_name():
        # Skip name check in test mode if desired
        if not current_user.is_authenticated:
            return None

        roles = getattr(current_user, "roles", [])
        if (
            len(roles)
            and request.endpoint != "user.your_account"
            and (
                not getattr(current_user, "first_name", None)
                or not getattr(current_user, "last_name", None)
            )
        ):
            flash("You must fill your name in to use ENRG DocDB!", "error")
            return redirect(url_for("user.your_account"))


def _roles_have_permission(
    user: User, organization_id: int | None, permission: RolePermission
):
    for role in user.roles:
        # Sidenote: None organization_id means all organizations
        if (
            organization_id
            and role.organization_id
            and role.organization_id != organization_id
        ):
            continue

        if permission.value in role.permissions:
            return True
    return False


def _is_super_admin(user: User):
    for role in user.roles:
        if role.organization_id is None and RolePermission.ADMIN in role.permissions:
            return True
    return False


def _has_wiki_page_permission(
    user: User, page: WikiPage, action: RolePermission
) -> bool:
    current_page = page
    processed_permissions = 0
    while current_page:
        for perm in current_page.permissions:
            processed_permissions += 1
            # Check if user has this role
            if not any(role.id == perm.role_id for role in user.roles):
                continue
            # Exact match
            if perm.permission == action:
                return True
        # Inherit parent permissions (additive)
        current_page = current_page.parent_page

    # If no permission has been defined for any of the pages...
    if (
        processed_permissions == 0
        # And if the user wants only to view...
        and action == RolePermission.VIEW
        # Match organizations:
        and (
            # If the page has no organization
            page.organization_id is None
            # Or the user has access to the organization
            or any(role.organization_id == page.organization_id for role in user.roles)
        )
    ):
        # The user may access then
        return True
    return False


def permission_check(model: Any, action: RolePermission):
    user: User | None = current_user  # type: ignore
    if not user or not user.is_authenticated:
        return False
    if _is_super_admin(user):
        return True

    organization_id = None

    try:
        with limiter.limit(RATELIMIT_NON_VIEW_ACTIONS):
            pass
    except RateLimitExceeded:
        flash("You have exceeded the rate limit! Please try again later.", "error")
        return False
    # Try to get the organization_id from the model
    if model:
        if isinstance(model, Document):
            organization_id = model.organization_id
            # Allow editing self document
            if model.user_id == user.id and action == RolePermission.EDIT:
                action = RolePermission.EDIT_SELF
        # Allow everyone to add authors
        elif action == RolePermission.ADD and model is Author:
            return True
        elif isinstance(model, WikiPage):
            return _has_wiki_page_permission(user, model, action)
        elif hasattr(model, "page") and isinstance(model.page, WikiPage):
            # For WikiFile and WikiRevision
            return _has_wiki_page_permission(user, model.page, action)
        elif hasattr(model, "organization_id"):
            organization_id = model.organization_id
        elif hasattr(model, "document_id") or hasattr(model, "document"):
            if hasattr(model, "document"):
                organization_id = model.document.organization_id
            else:
                document = (
                    db.session.query(Document).filter_by(id=model.document_id).first()
                )
                if document:
                    organization_id = document.organization_id
        elif isinstance(model, User):
            has_permission = False
            for target_role in model.roles:
                if _roles_have_permission(user, target_role.organization_id, action):
                    has_permission = True

            return has_permission

        # If no organization_id is found, only allow VIEW
        if not organization_id and action == RolePermission.VIEW:
            return True

    return _roles_have_permission(user, organization_id, action)
