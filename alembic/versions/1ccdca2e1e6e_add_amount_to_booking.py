"""Add amount to booking

Revision ID: 1ccdca2e1e6e
Create Date: 2018-07-26 11:52:17.853134

"""
from alembic import op

# revision identifiers, used by Alembic.

revision = '1ccdca2e1e6e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        'ALTER TABLE "booking" ADD COLUMN amount numeric(10,2) NOT NULL;'
        'ALTER TABLE "booking" ALTER COLUMN "stockId" SET NOT NULL;'
    )


def downgrade():
    pass
