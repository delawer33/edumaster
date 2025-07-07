from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import PaymentTransaction
from app.schemas import SCoursePaymentRequest


class PaymentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_transaction(
        self, payment_data: SCoursePaymentRequest, user_id: int
    ) -> PaymentTransaction:
        transaction = PaymentTransaction(
            course_id=payment_data.course_id,
            user_id=user_id,
            currency=payment_data.currency,
            card_token=payment_data.card_token,
            status="success",
            message="Тестовый платеж (заглушка)",
        )

        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction

    async def get_transaction(
        self, transaction_id: int
    ) -> PaymentTransaction | None:
        stmt = select(PaymentTransaction).where(
            PaymentTransaction.id == transaction_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
