import logging
import struct
import traceback
from functools import lru_cache
from typing import Any, Optional

from flask_security.utils import verify_password
from ldaptor.inmemory import ReadOnlyInMemoryLDAPEntry
from ldaptor.protocols import pureldap
from ldaptor.protocols.ldap import distinguishedname, ldaperrors
from ldaptor.protocols.ldap.ldapserver import LDAPServer
from OpenSSL import SSL
from sqlalchemy.orm import joinedload
from twisted.internet import defer, reactor
from twisted.internet.endpoints import serverFromString
from twisted.internet.interfaces import IReactorCore
from twisted.internet.protocol import ServerFactory

from src.enrgdocdb.database import db
from src.enrgdocdb.models.user import Role, User

logger = logging.getLogger(__name__)


class DocDBLDAPServer(LDAPServer):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.base_dn = app.config.get("LDAP_BASE_DN", "dc=enrgdocdb")
        self.users_ou = f"{app.config.get('LDAP_USERS_OU', 'ou=users')},{self.base_dn}"
        self.groups_ou = (
            f"{app.config.get('LDAP_GROUPS_OU', 'ou=groups')},{self.base_dn}"
        )
        self.bound_dn = b""
        self.use_tls = app.config.get("LDAP_USE_TLS", False)
        self.tls_cert_file = app.config.get("LDAP_TLS_CERT_FILE")
        self.tls_key_file = app.config.get("LDAP_TLS_KEY_FILE")
        self.tls_ca_file = app.config.get("LDAP_TLS_CA_FILE")
        self.cache_enabled = app.config.get("LDAP_CACHE_ENABLED", False)
        self.page_size = app.config.get("LDAP_PAGE_SIZE", 1000)

    # Shared cache for mapping UID string to database ID (persists across connections)
    _uid_to_id_cache = {}

    def get_user_by_generated_uid(self, uid_str):
        """Find a user by their LDAP-generated UID."""
        if not self.cache_enabled:
            return self._uncached_get_user_by_generated_uid(uid_str)

        # Check in-memory dict cache
        user_id = DocDBLDAPServer._uid_to_id_cache.get(uid_str)
        if user_id:
            user = self.get_user_by_uuid(user_id)
            if user:
                return user
            # If ID in cache but user not found, clear cache entry
            DocDBLDAPServer._uid_to_id_cache.pop(uid_str, None)

        user = self._uncached_get_user_by_generated_uid(uid_str)
        if user:
            DocDBLDAPServer._uid_to_id_cache[uid_str] = user.id
        return user

    def get_users(self, with_roles=False):
        """Get all active users with optional eager loading."""

        with self.app.app_context():
            query = db.session.query(User).filter_by(deleted_at=None, active=True)
            if with_roles:
                # Eager load roles to avoid N+1 queries

                query = query.options(joinedload(User.roles))
            return query.all()

    def get_user_by_uuid(self, uuid_str):

        with self.app.app_context():
            try:
                # Use UUID directly for fs_uniquifier or id
                return (
                    db.session.query(User)
                    .filter(
                        (User.id == uuid_str) | (User.fs_uniquifier == uuid_str),
                        User.deleted_at.is_(None),
                        User.active.is_(True),
                    )
                    .first()
                )
            except Exception as e:
                logger.error(f"Error fetching user by UUID {uuid_str}: {e}")
                return None

    def get_user_by_email(self, email):

        with self.app.app_context():
            return (
                db.session.query(User)
                .filter_by(email=email, deleted_at=None, active=True)
                .first()
            )

    # get_user_by_generated_uid moved up for better structure

    def _uncached_get_user_by_generated_uid(self, uid_str):
        """Query database directly for user with matching username."""

        with self.app.app_context():
            # 1. Direct query on new username field (Fastest)
            user = db.session.query(User).filter(
                (User.username == uid_str),
                User.deleted_at.is_(None),
                User.active.is_(True)
            ).first()
            if user:
                return user

            # 2. Fallback to scanning if username is not yet populated (Legacy/Graceful)
            users = self.get_users()
            for u in users:
                if u.get_ldap_uid() == uid_str:
                    return u
            return None

    def get_roles(self):
        """Get all roles."""

        with self.app.app_context():
            return db.session.query(Role).all()

    def _generate_username(self, user):
        """Deprecated: Use user.get_ldap_uid() instead."""
        return user.get_ldap_uid()

    def _user_to_entry(self, user):
        """Convert a User to LDAP entry."""
        gen_uid = user.get_ldap_uid()
        dn = f"uid={gen_uid},{self.users_ou}"
        object_classes = [b"inetOrgPerson", b"organizationalPerson", b"person", b"top"]

        attributes = {
            "objectClass": object_classes,
            "uid": [gen_uid.encode("utf-8")],
            "mail": [user.email.encode("utf-8")],
            "cn": [user.name.encode("utf-8")],
            "sn": [
                user.last_name.encode("utf-8")
                if getattr(user, "last_name", None)
                else b"Unknown"
            ],
            "givenName": [
                user.first_name.encode("utf-8")
                if getattr(user, "first_name", None)
                else b"Unknown"
            ],
        }

        # Add displayName if different from cn
        if user.name and user.name != user.email:
            attributes["displayName"] = [user.name.encode("utf-8")]

        # Add userPrincipalName (email as UPN)
        attributes["userPrincipalName"] = [f"{user.email}".encode("utf-8")]

        # Add memberOf (group memberships)
        if hasattr(user, "roles") and user.roles:
            member_of = []
            for role in user.roles:
                role_dn = f"cn={role.name.lower()},{self.groups_ou}"
                member_of.append(role_dn.encode("utf-8"))
            attributes["memberOf"] = member_of

        return ReadOnlyInMemoryLDAPEntry(dn, attributes)

    def _role_to_entry(self, role, users_list=None, user_uid_cache=None):
        """Convert a Role to LDAP entry with member DNs."""

        dn = f"cn={role.name.lower()},{self.groups_ou}"
        object_classes = [b"groupOfNames", b"top"]

        members = []
        if user_uid_cache is None:
            user_uid_cache = {}

        # Get users for this role efficiently
        try:
            if users_list is not None:
                # Use pre-filtered list of users passed from caller
                users = [u for u in users_list if role in u.roles]
            else:
                # Fallback: query users for this role
                users = (
                    db.session.query(User)
                    .join(User.roles)
                    .filter(
                        Role.id == role.id,
                        User.deleted_at.is_(None),
                        User.active.is_(True),
                    )
                    .all()
                )

            for user in users:
                # Use cached UID if available
                if user.id in user_uid_cache:
                    gen_uid = user_uid_cache[user.id]
                else:
                    gen_uid = user.get_ldap_uid()
                    user_uid_cache[user.id] = gen_uid

                user_dn = f"uid={gen_uid},{self.users_ou}"
                members.append(user_dn.encode("utf-8"))
        except Exception as e:
            logger.error(f"Error fetching members for role {role.name}: {e}")

        attributes = {
            "objectClass": object_classes,
            "cn": [role.name.encode("utf-8")],
            "member": members,
        }
        if getattr(role, "description", None):
            attributes["description"] = [role.description.encode("utf-8")]

        return ReadOnlyInMemoryLDAPEntry(dn, attributes)

    def handle_LDAPSearchRequest(self, request, controls, reply):
        try:
            base_dn_str = request.baseObject.decode("utf-8")
            logger.debug(f"LDAP Search: base={base_dn_str}, filter={request.filter}")

            # Check for paged results control (1.2.840.113556.1.4.319)
            paged_control = None
            if controls:
                for control in controls:
                    if control.controlType == b"1.2.840.113556.1.4.319":
                        paged_control = control
                        break

            # Handle everything within a single app context for session consistency
            with self.app.app_context():
                # Fetch all users with roles eagerly loaded
                users = self.get_users(with_roles=True)
                # Build UID cache to avoid re-computing
                user_uid_cache = {}
                user_entries = []
                for u in users:
                    gen_uid = u.get_ldap_uid()
                    user_uid_cache[u.id] = gen_uid
                    entry = self._user_to_entry(u)
                    user_entries.append(entry)

                # Fetch all roles
                roles = self.get_roles()

                # Build role entries using the preloaded users list to avoid N+1
                role_entries = [
                    self._role_to_entry(r, users, user_uid_cache) for r in roles
                ]

            entries = []

            if request.baseObject == b"":
                root = ReadOnlyInMemoryLDAPEntry(
                    distinguishedname.DistinguishedName(b""),
                    {
                        "objectClass": [b"top"],
                        "namingContexts": [self.base_dn.encode("utf-8")],
                        "supportedLDAPVersion": [b"3"],
                        "supportedControl": [
                            b"1.2.840.113556.1.4.319",  # Paged Results
                            b"1.3.6.1.4.1.4203.1.11.3",  # WhoAmI
                        ],
                    },
                )
                entries.append(root)

            # organizational unit for users
            ou_users_entry = ReadOnlyInMemoryLDAPEntry(
                distinguishedname.DistinguishedName(self.users_ou),
                {
                    "objectClass": [b"organizationalUnit", b"top"],
                    "ou": [b"users"],
                },
            )
            entries.append(ou_users_entry)

            # organizational unit for groups
            ou_groups_entry = ReadOnlyInMemoryLDAPEntry(
                distinguishedname.DistinguishedName(self.groups_ou),
                {
                    "objectClass": [b"organizationalUnit", b"top"],
                    "ou": [b"groups"],
                },
            )
            entries.append(ou_groups_entry)

            entries.extend(user_entries)
            entries.extend(role_entries)

            matched = []
            search_base = distinguishedname.DistinguishedName(base_dn_str)

            for entry in entries:
                try:
                    # Check if entry is within the search base
                    if not search_base.contains(entry.dn):
                        continue

                    is_match = entry.match(request.filter)
                    if is_match:
                        matched.append(entry)
                except Exception as e:
                    logger.warning(f"Filter error for {entry.dn}: {e}")

            # Handle paged results if requested
            total_matched = len(matched)
            start_index = 0
            if paged_control:

                try:
                    value = paged_control.controlValue
                    if value:
                        # Improved BER parsing for paged results would go here.
                        # For now, we use a simple string-based cookie for index.
                        page_size = self.page_size
                        
                        if len(value) > 2:
                            try:
                                # Try to detect a simple string index in the cookie field
                                cookie_part = value[2:] if value[0] == 0x30 else value
                                start_index = int(cookie_part.decode("utf-8", errors="ignore"))
                            except (ValueError, TypeError):
                                start_index = 0
                    else:
                        page_size = self.page_size
                except Exception as e:
                    logger.error(f"Error parsing paged results control: {e}")
                    page_size = self.page_size
            else:
                page_size = total_matched

            paged_results = matched[start_index : start_index + page_size]

            # Generate cookie for next page if needed
            next_cookie = b""
            if start_index + page_size < total_matched:
                next_index = start_index + page_size
                # Simple integer encoding for cookie
                next_cookie = str(next_index).encode("utf-8")

            for entry in paged_results:
                attributes = []
                for k, v in entry.items():
                    attributes.append(
                        (k.encode("utf-8") if isinstance(k, str) else k, list(v))
                    )
                resp = pureldap.LDAPSearchResultEntry(
                    objectName=str(entry.dn).encode("utf-8"), attributes=attributes
                )
                reply(resp)

            # Create response with paged results control if cookie exists
            response_controls = []
            if next_cookie:
                paged_response_control = pureldap.LDAPControl(
                    controlType=b"1.2.840.113556.1.4.319",
                    criticality=False,
                    controlValue=struct.pack("<I", page_size) + next_cookie,
                )
                response_controls.append(paged_response_control)

            return defer.succeed(
                pureldap.LDAPSearchResultDone(
                    resultCode=ldaperrors.Success.resultCode,
                    matchedDN=b"",
                    errorMessage=b"",
                    controls=response_controls if response_controls else None,
                )
            )
        except Exception as e:
            logger.error(f"LDAP Search error: {e}", exc_info=True)
            return defer.succeed(
                pureldap.LDAPSearchResultDone(
                    resultCode=ldaperrors.LDAPOperationsError.resultCode,
                    matchedDN=b"",
                    errorMessage=str(e).encode("utf-8")[:256],
                )
            )

    def handle_LDAPBindRequest(self, request, controls, reply):
        logger.debug(f"LDAP Bind: DN={request.dn}, has_auth={bool(request.auth)}")

        if not request.dn and not request.auth:
            self.bound_dn = b""
            logger.debug("Anonymous bind successful")
            return defer.succeed(
                pureldap.LDAPBindResponse(
                    resultCode=ldaperrors.Success.resultCode,
                    matchedDN=b"",
                    errorMessage=b"",
                )
            )

        try:
            dn = request.dn.decode("utf-8")
            password = request.auth.decode("utf-8") if request.auth else ""
        except Exception as e:
            logger.warning(f"Bind request decode error: {e}")
            return defer.succeed(
                pureldap.LDAPBindResponse(
                    resultCode=ldaperrors.LDAPInvalidCredentials.resultCode,
                    matchedDN=b"",
                    errorMessage=b"Invalid credentials format",
                )
            )

        # Check for secure bind requirement
        if self.app.config.get("LDAP_REQUIRE_SECURE_BINDS", False) and not self.use_tls:
            logger.warning("Secure binds required but TLS not enabled")
            return defer.succeed(
                pureldap.LDAPBindResponse(
                    resultCode=ldaperrors.LDAPStrongAuthRequired.resultCode,
                    matchedDN=b"",
                    errorMessage=b"Secure bind required",
                )
            )

        admin_password = self.app.config.get("LDAP_ADMIN_PASSWORD")
        if admin_password and dn == f"cn=admin,{self.base_dn}":
            if password == admin_password:
                self.bound_dn = request.dn
                logger.info(f"Admin bind successful from DN: {dn}")
                return defer.succeed(
                    pureldap.LDAPBindResponse(
                        resultCode=ldaperrors.Success.resultCode,
                        matchedDN=b"",
                        errorMessage=b"",
                    )
                )
            else:
                logger.warning(f"Failed admin bind attempt from DN: {dn}")
                return defer.succeed(
                    pureldap.LDAPBindResponse(
                        resultCode=ldaperrors.LDAPInvalidCredentials.resultCode,
                        matchedDN=b"",
                        errorMessage=b"Invalid credentials",
                    )
                )

        if dn.lower().endswith(self.users_ou.lower()):
            parts = dn.split(",")
            uid_part = parts[0]
            user = None

            # Wrap in app context
            with self.app.app_context():
                # Support binding with uid=, cn=, mail=
                if uid_part.startswith("uid="):
                    uid = uid_part[4:]
                    user = self.get_user_by_generated_uid(uid)
                    if not user:
                        user = self.get_user_by_email(uid)
                elif uid_part.startswith("cn="):
                    cn_val = uid_part[3:]
                    user = self.get_user_by_email(cn_val)
                elif uid_part.startswith("mail="):
                    mail_val = uid_part[5:]
                    user = self.get_user_by_email(mail_val)

                if user:
                    if not user.active:
                        logger.warning(
                            f"Bind attempted for inactive user: {user.email}"
                        )
                        return defer.succeed(
                            pureldap.LDAPBindResponse(
                                resultCode=ldaperrors.LDAPInvalidCredentials.resultCode,
                                matchedDN=b"",
                                errorMessage=b"User account is disabled",
                            )
                        )

                    if user.deleted_at:
                        logger.warning(f"Bind attempted for deleted user: {user.email}")
                        return defer.succeed(
                            pureldap.LDAPBindResponse(
                                resultCode=ldaperrors.LDAPInvalidCredentials.resultCode,
                                matchedDN=b"",
                                errorMessage=b"User account has been deleted",
                            )
                        )

                    if user.password is None:
                        logger.error(f"User {user.email} has no password set")
                        return defer.succeed(
                            pureldap.LDAPBindResponse(
                                resultCode=ldaperrors.LDAPInvalidCredentials.resultCode,
                                matchedDN=b"",
                                errorMessage=b"Invalid credentials",
                            )
                        )

                    is_valid = verify_password(password, user.password)
                    if is_valid:
                        self.bound_dn = request.dn
                        logger.info(f"User bind successful: {user.email}")
                        return defer.succeed(
                            pureldap.LDAPBindResponse(
                                resultCode=ldaperrors.Success.resultCode,
                                matchedDN=b"",
                                errorMessage=b"",
                            )
                        )
                    else:
                        logger.warning(f"Invalid password for user: {user.email}")

        logger.warning(f"Bind failed for DN: {dn}")
        return defer.succeed(
            pureldap.LDAPBindResponse(
                resultCode=ldaperrors.LDAPInvalidCredentials.resultCode,
                matchedDN=b"",
                errorMessage=b"Invalid credentials",
            )
        )

    def extendedRequest_whoami(self, value=None, reply=None):
        authz_id = b"dn:" + self.bound_dn if self.bound_dn else b""
        logger.debug(f"WhoAmI request: {authz_id.decode('utf-8', errors='ignore')}")
        return pureldap.LDAPExtendedResponse(
            resultCode=ldaperrors.Success.resultCode,
            response=authz_id,
        )

    extendedRequest_whoami.oid = b"1.3.6.1.4.1.4203.1.11.3"


def create_ldap_server(app, port: Optional[int] = None, use_tls: bool = False):
    """Create and return an LDAP server endpoint."""

    if port is None:
        port = app.config.get("LDAP_PORT", 10389)

    class LDAPFactory(ServerFactory):
        def buildProtocol(self, addr):
            proto = DocDBLDAPServer(app)
            proto.factory = self
            return proto

    endpoint_str = f"tcp:{port}"
    endpoint = serverFromString(reactor, endpoint_str)
    endpoint.listen(LDAPFactory())
    logger.info(f"DocDB LDAP Server listening on port {port}, TLS={use_tls}")
    return endpoint


def run_ldap_server(app, port: Optional[int] = None):
    """Run the LDAP server (blocking)."""

    if port is None:
        port = app.config.get("LDAP_PORT", 10389)
    create_ldap_server(app, port)
    reactor.run()  # type: ignore[attr-defined]
