"""add retry state to delivery_attempts

Revision ID: a4f1c9d2e7b3
Revises: 623ac0e6e525
Create Date: 2026-08-30 10:14:22.108734
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a4f1c9d2e7b3'
down_revision: Union[str, None] = '623ac0e6e525'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # outcome is NOT NULL in the model, but delivery_attempts already has rows
    # on the deployed database. Postgres will not add a NOT NULL column to a
    # populated table without a value for the existing rows, so this is three
    # steps: add nullable, backfill, then tighten the constraint.
    op.add_column(
        'delivery_attempts',
        sa.Column('outcome', sa.String(length=20), nullable=True),
    )
    op.add_column(
        'delivery_attempts',
        sa.Column('error_type', sa.String(length=100), nullable=True),
    )
    op.add_column(
        'delivery_attempts',
        sa.Column('computed_delay_ms', sa.Integer(), nullable=True),
    )
    op.add_column(
        'delivery_attempts',
        sa.Column('applied_delay_ms', sa.Integer(), nullable=True),
    )
    op.add_column(
        'delivery_attempts',
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
    )

    # Backfill using the same boundaries classify() applies, so historical rows
    # agree with rows written from now on. A NULL response_status means the
    # request raised: before this migration the only handler was
    # `except httpx.RequestError`, and classify() maps every RequestError it
    # sees to RETRY apart from UnsupportedProtocol and LocalProtocolError, so
    # 'retry' is the best available reading of those rows.
    op.execute(
        """
        UPDATE delivery_attempts
        SET outcome = CASE
            WHEN response_status IS NULL THEN 'retry'
            WHEN response_status = 429 THEN 'retry'
            WHEN response_status BETWEEN 200 AND 299 THEN 'success'
            WHEN response_status BETWEEN 400 AND 499 THEN 'terminal'
            WHEN response_status BETWEEN 500 AND 599 THEN 'retry'
            WHEN response_status < 200 THEN 'retry'
            ELSE 'terminal'
        END
        """
    )

    op.alter_column('delivery_attempts', 'outcome', nullable=False)


def downgrade() -> None:
    op.drop_column('delivery_attempts', 'next_attempt_at')
    op.drop_column('delivery_attempts', 'applied_delay_ms')
    op.drop_column('delivery_attempts', 'computed_delay_ms')
    op.drop_column('delivery_attempts', 'error_type')
    op.drop_column('delivery_attempts', 'outcome')
