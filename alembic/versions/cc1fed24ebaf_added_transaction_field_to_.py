"""added transaction field to CoursePurchase

Revision ID: cc1fed24ebaf
Revises: 5660bf1fdf20
Create Date: 2025-07-06 22:11:54.361021

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc1fed24ebaf'
down_revision: Union[str, None] = '5660bf1fdf20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('course_purchases',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_course_purchases'))
    )
    op.create_index(op.f('ix_course_purchases_id'), 'course_purchases', ['id'], unique=False)
    op.create_table('payment_transactions',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('transaction_id', sa.Uuid(as_uuid=False), nullable=False),
    sa.Column('course_id', sa.Integer(), nullable=False),
    sa.Column('user_email', sa.String(length=255), nullable=False),
    sa.Column('amount', sa.Float(precision=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('card_token', sa.String(length=100), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('message', sa.String(length=255), nullable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_payment_transactions'))
    )
    op.create_index(op.f('ix_payment_transactions_transaction_id'), 'payment_transactions', ['transaction_id'], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_payment_transactions_transaction_id'), table_name='payment_transactions')
    op.drop_table('payment_transactions')
    op.drop_index(op.f('ix_course_purchases_id'), table_name='course_purchases')
    op.drop_table('course_purchases')
    # ### end Alembic commands ###
