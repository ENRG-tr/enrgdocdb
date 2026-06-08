"""update_user_role_permissions

Revision ID: 1773780471
Revises: 1773780470
Create Date: 2026-06-08 22:50:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "1773780471"
down_revision: Union[str, None] = "1773780470"
branch_labels: Union[str, Sequence[str], None] = ()
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    
    # Update existing "user" roles to include ADD and EDIT if missing
    # role.permissions is stored as a JSON list
    
    # Fetch all "user" roles
    roles = connection.execute(
        sa.text("SELECT id, permissions FROM role WHERE name = 'user'")
    ).fetchall()
    
    for role_id, permissions in roles:
        if permissions is None:
            permissions = []
        # Ensure we work with a list
        if isinstance(permissions, str):
            import json
            permissions = json.loads(permissions)
        
        new_perms = set(permissions)
        added = False
        if "ADD" not in new_perms:
            new_perms.add("ADD")
            added = True
        if "EDIT" not in new_perms:
            new_perms.add("EDIT")
            added = True
        
        if added:
            connection.execute(
                sa.text("UPDATE role SET permissions = :permissions WHERE id = :id"),
                {"permissions": sorted(list(new_perms)), "id": role_id},
            )


def downgrade() -> None:
    # Revert: remove ADD and EDIT from "user" roles that had them added
    connection = op.get_bind()
    
    roles = connection.execute(
        sa.text("SELECT id, permissions FROM role WHERE name = 'user'")
    ).fetchall()
    
    for role_id, permissions in roles:
        if permissions is None:
            continue
        if isinstance(permissions, str):
            import json
            permissions = json.loads(permissions)
        
        new_perms = [p for p in permissions if p not in ("ADD", "EDIT")]
        if len(new_perms) != len(permissions):
            connection.execute(
                sa.text("UPDATE role SET permissions = :permissions WHERE id = :id"),
                {"permissions": new_perms, "id": role_id},
            )
