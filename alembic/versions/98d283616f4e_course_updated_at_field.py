"""Course updated_at field

Revision ID: 98d283616f4e
Revises: 52bd4bf656dd
Create Date: 2025-06-18 11:47:57.812527

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '98d283616f4e'
down_revision: Union[str, None] = '52bd4bf656dd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('courses', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True))

    op.execute("UPDATE courses SET updated_at = NOW()")

    op.alter_column('courses', 'updated_at', nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('courses', 'updated_at')
    # ### end Alembic commands ###
