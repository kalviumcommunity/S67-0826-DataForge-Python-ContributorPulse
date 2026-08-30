"""Add contributor experience level, maintainer flag, weekend flag, and risk reason.

Revision ID: 002_feature_engine_fields
Revises: 001_initial_schema
Create Date: 2026-08-30
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_feature_engine_fields"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add experience_level, is_active_maintainer, has_weekend_contributions, and risk_reason columns."""
    op.add_column(
        "contributor_features",
        sa.Column("experience_level", sa.String(length=50), nullable=False, server_default="first_time"),
    )
    op.add_column(
        "contributor_features",
        sa.Column("is_active_maintainer", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "contributor_features",
        sa.Column("has_weekend_contributions", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "contributor_features",
        sa.Column("risk_reason", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    """Remove added columns from contributor_features."""
    op.drop_column("contributor_features", "risk_reason")
    op.drop_column("contributor_features", "has_weekend_contributions")
    op.drop_column("contributor_features", "is_active_maintainer")
    op.drop_column("contributor_features", "experience_level")
