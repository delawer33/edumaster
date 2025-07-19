from fastapi import Depends, APIRouter, status, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import (
    get_async_db_session,
    CoursePurchase,
    User,
    PaymentTransaction,
)
from app.dependencies import get_current_user
from app.schemas import SPaymentResponse, SCoursePaymentRequest
from app.helpers import payments

from datetime import datetime
from app.core.rabbitmq import publish_message
import uuid

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/stub", response_model=SPaymentResponse)
async def process_payment_stub(
    request: SCoursePaymentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session),
):
    try:
        stmt_check_purchase = select(CoursePurchase).where(
            CoursePurchase.user_id == user.id,
            CoursePurchase.course_id == request.course_id,
        )
        existing_purchase = await db.execute(stmt_check_purchase)
        if existing_purchase.scalars().first() is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Курс уже приобретен.",
            )

        payment_intent_id = str(uuid.uuid4())

        payment_data = {
            "payment_intent_id": payment_intent_id,
            "course_id": request.course_id,
            "currency": request.currency,
            "card_token": request.card_token,
            "user_id": user.id,
        }
        await publish_message("payment_requests_queue", payment_data)

        return SPaymentResponse(
            status="pending",
            payment_intent_id=payment_intent_id,
            transaction_id=None,
            currency=request.currency,
            timestamp=datetime.now(),
            message=f"Запрос на платеж за курс #{request.course_id} отправлен на обработку",
            course_id=request.course_id,
        )
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка базы данных",
        )

    except HTTPException as e:
        await db.rollback()
        raise e

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/stub/{transaction_id}", response_model=SPaymentResponse)
async def get_payment_status(
    transaction_id: int, db: AsyncSession = Depends(get_async_db_session)
):
    repo = payments.PaymentRepository(db)
    transaction = await repo.get_transaction(transaction_id)

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Транзакция не найдена",
        )

    return SPaymentResponse(
        status=transaction.status,
        transaction_id=transaction.id,
        currency=transaction.currency,
        timestamp=transaction.created_at,
        message=transaction.message or "Статус платежа",
        course_id=transaction.course_id,
    )


@router.get("/status/{payment_intent_id}", response_model=SPaymentResponse)
async def get_payment_status_by_intent(
    payment_intent_id: str, db: AsyncSession = Depends(get_async_db_session)
):
    stmt = select(PaymentTransaction).where(
        PaymentTransaction.payment_intent_id == payment_intent_id
    )
    transaction_result = await db.execute(stmt)
    transaction = transaction_result.scalars().first()

    if not transaction:
        return SPaymentResponse(
            status="not_found_or_pending",
            payment_intent_id=payment_intent_id,
            transaction_id=None,
            currency="N/A",
            timestamp=datetime.now(),
            message="Payment intent not found or still being processed.",
            course_id=0,
        )

    return SPaymentResponse(
        status=transaction.status,
        transaction_id=transaction.id,
        currency=transaction.currency,
        timestamp=transaction.created_at,
        message=transaction.message or "Статус платежа",
        course_id=transaction.course_id,
        payment_intent_id=payment_intent_id,
    )
