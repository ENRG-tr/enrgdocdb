"""update_user_role_permissions

Revision ID: 1773780471
Revises: 1773780470
Create Date: 2026-06-08 22:50:00.000000

"""

import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "1773780471"
down_revision: Union[str, None] = "1773780470"
branch_labels: Union[str, Sequence[str], None] = ()
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # AsaList stores permissions as JSON text; fetch raw, parse, update, write back
    rows = bind.execute(
        sa.text("SELECT id, permissions FROM role WHERE name = 'user'")
    ).fetchall()

    for row_id, raw in rows:
        # raw may be a JSON string, or None, or already a list
        if raw is None or raw == "":
            perms = []
        elif isinstance(raw, str):
            perms = json.loads(raw)
        else:
            # Already deserialized by the driver (JSON column)
            perms = list(raw)

        new_perms = set(perms)
        if "ADD" not in new_perms:
            new_perms.add("ADD")
        if "EDIT" not in new_perms:
            new_perms.add("EDIT")

        if set(perms) != new_perms:
            write_val = json.dumps(sorted(new_perms))
            bind.execute(
                sa.text("UPDATE role SET permissions = :p WHERE id = :id"),
                {"p": write_val, "id": row_id},
            )


def downgrade() -> None:
    bind = op.get_bind()

    rows = bind.execute(
        sa.text("SELECT id, permissions FROM role WHERE name = 'user'")
    ).fetchall()

    for row_id, raw in rows:
        if raw is None or raw == "":
            continue
        elif isinstance(raw, str):
            perms = json.loads(raw)
        else:
            perms = list(raw)

        new_perms = [p for p in perms if p not in ("ADD", "EDIT")]
        if set(perms) != set(new_perms):
            write_val = json.dumps(new_perms)
            bind.execute(
                sa.text("UPDATE role SET permissions = :p WHERE id = :id"),
                {"p": write_val, "id": row_id},
            )
