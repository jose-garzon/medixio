"""patient prepaid plan

Revision ID: c1a2d3e4f5a6
Revises: b7450908f790
Create Date: 2026-11-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op


revision: str = "c1a2d3e4f5a6"
down_revision: str | Sequence[str] | None = "b7450908f790"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("patientprofile") as batch_op:
        batch_op.add_column(
            sa.Column("prepaid_plan", sqlmodel.sql.sqltypes.AutoString(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("patientprofile") as batch_op:
        batch_op.drop_column("prepaid_plan")
