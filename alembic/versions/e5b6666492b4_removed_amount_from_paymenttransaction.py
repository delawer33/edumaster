"""removed amount from PaymentTransaction

Revision ID: e5b6666492b4
Revises: fa23906140b7
Create Date: 2025-07-07 12:31:57.478398

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5b6666492b4'
down_revision: Union[str, None] = 'fa23906140b7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('payment_transactions', 'amount')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('payment_transactions', sa.Column('amount', sa.REAL(), autoincrement=False, nullable=False))
    # ### end Alembic commands ###
