from fastapi import (
    Depends,
    APIRouter,
    status,
    HTTPException
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import (
    get_async_db_session,
    CoursePurchase,
    User
)
from app.dependencies import (
    get_current_user
)
from app.schemas import (
    SPaymentResponse,
    SCoursePaymentRequest
)
from app.helpers import (
    payments,
    obj_exist_check
)

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/stub", response_model=SPaymentResponse)
async def process_payment_stub(
    request: SCoursePaymentRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db_session)
):
    repo = payments.PaymentRepository(db)

    stmt = select(CoursePurchase).where(
        CoursePurchase.user_id == user.id
    )

    cp = await db.execute(stmt)

    cp = cp.scalars().first()
    if cp is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Курс приобретен"
        )

    payment_data = SCoursePaymentRequest(
        course_id=request.course_id,
        currency=request.currency,
        card_token=request.card_token
    )

    transaction = await repo.create_transaction(payment_data, user_id=user.id)

    course = await obj_exist_check.course_exists(request.course_id, db)

    if transaction.status == "success":
        cp = CoursePurchase(
            user_id=user.id,
            course_id=course.id,
            transaction_id=transaction.id
        )

        db.add(cp)
        await db.commit()

    return SPaymentResponse(
        status=transaction.status,
        transaction_id=transaction.id,
        currency=transaction.currency,
        timestamp=transaction.created_at,
        message=f"Тестовый платеж за курс #{request.course_id} успешно обработан",
        course_id=transaction.course_id
    )


@router.get(
        "/stub/{transaction_id}",
        response_model=SPaymentResponse
        )
async def get_payment_status(
    transaction_id: int,
    db: AsyncSession = Depends(get_async_db_session)
):
    repo = payments.PaymentRepository(db)
    transaction = await repo.get_transaction(transaction_id)

    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Транзакция не найдена"
        )

    return SPaymentResponse(
        status=transaction.status,
        transaction_id=transaction.id,
        currency=transaction.currency,
        timestamp=transaction.created_at,
        message=transaction.message or "Статус платежа",
        course_id=transaction.course_id
    )
