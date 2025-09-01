"""merge heads

Revision ID: 8ea178904eb8
Revises: 5472205a0c98, ba530ab945a2
Create Date: 2025-09-01 18:16:49.638447

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8ea178904eb8'
down_revision = ('5472205a0c98', 'ba530ab945a2')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
