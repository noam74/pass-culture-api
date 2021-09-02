"""add_type_to_deposit

Revision ID: 7ec4136ab598
Revises: 83d275671e3e
Create Date: 2021-08-31 13:05:56.051068

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7ec4136ab598"
down_revision = "83d275671e3e"
branch_labels = None
depends_on = None


DepositType = sa.Enum("GRANT_15", "GRANT_16", "GRANT_17", "GRANT_18", name="deposittype")


def upgrade():
    DepositType.create(op.get_bind(), checkfirst=True)
    op.add_column("deposit", sa.Column("type", DepositType, server_default="GRANT_18", nullable=False))


def downgrade():
    op.drop_column("deposit", "type")
