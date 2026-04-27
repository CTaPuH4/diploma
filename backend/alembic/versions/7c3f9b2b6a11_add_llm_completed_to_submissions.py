"""add llm completed flag

Revision ID: 7c3f9b2b6a11
Revises: a6b24795d00f
Create Date: 2026-04-27 15:35:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7c3f9b2b6a11"
down_revision: Union[str, None] = "a6b24795d00f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "submissions",
        sa.Column(
            "llm_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.execute(
        """
        UPDATE submissions
        SET llm_completed = CASE
            WHEN llm_comment IS NOT NULL THEN true
            ELSE false
        END
        """
    )
    op.alter_column("submissions", "llm_completed", server_default=None)


def downgrade() -> None:
    op.drop_column("submissions", "llm_completed")
