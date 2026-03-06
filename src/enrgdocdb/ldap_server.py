import logging
import traceback

from ldaptor.protocols import pureldap
from ldaptor.protocols.ldap import ldaperrors
from ldaptor.protocols.ldap.ldapserver import LDAPServer
from twisted.internet import defer
from ldaptor.protocols.ldap import distinguishedname
from ldaptor.inmemory import ReadOnlyInMemoryLDAPEntry

logger = logging.getLogger(__name__)


class DocDBLDAPServer(LDAPServer):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.base_dn = "dc=enrgdocdb"
        self.users_ou = f"ou=users,{self.base_dn}"
        self.bound_dn = b""

    def get_users(self):
        from src.enrgdocdb.database import db
        from src.enrgdocdb.models.user import User

        with self.app.app_context():
            return db.session.query(User).filter_by(deleted_at=None).all()

    def get_user_by_uuid(self, uuid_str):
        from src.enrgdocdb.database import db
        from src.enrgdocdb.models.user import User

        with self.app.app_context():
            try:
                return (
                    db.session.query(User)
                    .filter_by(id=uuid_str, deleted_at=None)
                    .first()
                )
            except Exception:
                return None

    def get_user_by_email(self, email):
        from src.enrgdocdb.database import db
        from src.enrgdocdb.models.user import User

        with self.app.app_context():
            return (
                db.session.query(User).filter_by(email=email, deleted_at=None).first()
            )

    def _generate_username(self, user):
        import re

        def transliterate(text):
            charmap = {
                "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
                "Ç": "c", "Ğ": "g", "İ": "i", "Ö": "o", "Ş": "s", "Ü": "u"
            }
            res = ""
            for char in text:
                res += str(charmap.get(char, char))
            return res

        f_name = transliterate((user.first_name or "").strip().lower())
        l_name = transliterate((user.last_name or "").strip().lower())

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
            email_part = transliterate((user.email or "").split("@")[0].lower())
            uid_str = re.sub(r"[^a-z0-9]", "", email_part)

        if not uid_str:
            uid_str = str(user.id)

        return uid_str

    def get_user_by_generated_uid(self, uid_str):
        users = self.get_users()
        for u in users:
            if self._generate_username(u) == uid_str:
                return u
        # try uuid fallback just in case
        return self.get_user_by_uuid(uid_str)

    def _user_to_entry(self, user):
        gen_uid = self._generate_username(user)
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
        if hasattr(user, "fs_uniquifier"):
            attributes["entryUUID"] = [str(user.fs_uniquifier).encode("utf-8")]

        return ReadOnlyInMemoryLDAPEntry(dn, attributes)

    def handle_LDAPSearchRequest(self, request, controls, reply):
        try:
            users = self.get_users()
            entries = [self._user_to_entry(u) for u in users]

            if request.baseObject == b"":
                root = ReadOnlyInMemoryLDAPEntry(
                    distinguishedname.DistinguishedName(b""),
                    {
                        "objectClass": [b"top"],
                        "namingContexts": [self.base_dn.encode("utf-8")],
                        "supportedLDAPVersion": [b"3"],
                    },
                )
                entries.append(root)

            # organizational unit for users
            ou_entry = ReadOnlyInMemoryLDAPEntry(
                distinguishedname.DistinguishedName(self.users_ou),
                {
                    "objectClass": [b"organizationalUnit", b"top"],
                    "ou": [b"users"],
                },
            )
            entries.append(ou_entry)

            matched = []
            for entry in entries:
                try:
                    is_match = entry.match(request.filter)
                    if is_match:
                        matched.append(entry)
                except Exception as e:
                    print(f"Filter error for {entry.dn}: {e}")

            for entry in matched:
                attributes = []
                for k, v in entry.items():
                    attributes.append(
                        (k.encode("utf-8") if isinstance(k, str) else k, list(v))
                    )
                resp = pureldap.LDAPSearchResultEntry(
                    objectName=str(entry.dn).encode("utf-8"), attributes=attributes
                )
                reply(resp)

            return defer.succeed(
                pureldap.LDAPSearchResultDone(
                    resultCode=ldaperrors.Success.resultCode,
                    matchedDN=b"",
                    errorMessage=b"",
                )
            )
        except Exception:
            traceback.print_exc()
            return defer.succeed(
                pureldap.LDAPSearchResultDone(
                    resultCode=ldaperrors.LDAPOperationsError.resultCode,
                    matchedDN=b"",
                    errorMessage=b"",
                )
            )

    def handle_LDAPBindRequest(self, request, controls, reply):
        if not request.dn and not request.auth:
            self.bound_dn = b""
            return defer.succeed(
                pureldap.LDAPBindResponse(
                    resultCode=ldaperrors.Success.resultCode,
                    matchedDN=b"",
                    errorMessage=b"",
                )
            )

        try:
            dn = request.dn.decode("utf-8")
            password = request.auth.decode("utf-8")
        except Exception:
            return defer.succeed(
                pureldap.LDAPBindResponse(
                    resultCode=ldaperrors.LDAPInvalidCredentials.resultCode,
                    matchedDN=b"",
                    errorMessage=b"",
                )
            )

        admin_password = self.app.config.get("LDAP_ADMIN_PASSWORD", "admin")
        if dn == f"cn=admin,{self.base_dn}" and password == admin_password:
            self.bound_dn = request.dn
            return defer.succeed(
                pureldap.LDAPBindResponse(
                    resultCode=ldaperrors.Success.resultCode,
                    matchedDN=b"",
                    errorMessage=b"",
                )
            )

        if dn.endswith(self.users_ou):
            parts = dn.split(",")
            uid_part = parts[0]
            user = None
            if uid_part.startswith("uid="):
                uid = uid_part[4:]
                user = self.get_user_by_generated_uid(uid)
                if not user:
                    user = self.get_user_by_email(uid)

                # Try CN (email for login in some systems or name?)
                # Wait, if uid= is not found, maybe they are binding with cn=email or mail=email?
                # Usually bind DNs specify the exact user representation

            # Let's also support binding with cn or mail directly, which many apps try
            if uid_part.startswith("cn="):
                cn_val = uid_part[3:]
                user = self.get_user_by_email(cn_val)
            if uid_part.startswith("mail="):
                mail_val = uid_part[5:]
                user = self.get_user_by_email(mail_val)

            if user:
                from flask_security.utils import verify_password

                with self.app.app_context():
                    is_valid = verify_password(password, user.password)
                    if is_valid:
                        self.bound_dn = request.dn
                        return defer.succeed(
                            pureldap.LDAPBindResponse(
                                resultCode=ldaperrors.Success.resultCode,
                                matchedDN=b"",
                                errorMessage=b"",
                            )
                        )

        return defer.succeed(
            pureldap.LDAPBindResponse(
                resultCode=ldaperrors.LDAPInvalidCredentials.resultCode,
                matchedDN=b"",
                errorMessage=b"",
            )
        )

    def extendedRequest_whoami(self, value=None, reply=None):
        authz_id = b"dn:" + self.bound_dn if self.bound_dn else b""
        # WhoAmI request does not return responseName
        return pureldap.LDAPExtendedResponse(
            resultCode=ldaperrors.Success.resultCode,
            response=authz_id,
        )

    extendedRequest_whoami.oid = b"1.3.6.1.4.1.4203.1.11.3"


def run_ldap_server(app, port=10389):
    from twisted.internet import protocol, reactor
    from twisted.internet.endpoints import serverFromString

    class LDAPFactory(protocol.ServerFactory):
        def buildProtocol(self, addr):
            proto = DocDBLDAPServer(app)
            proto.factory = self
            return proto

    endpoint = serverFromString(reactor, f"tcp:{port}")
    endpoint.listen(LDAPFactory())
    print(f"DocDB LDAP Server listening on {port}")
    reactor.run()
