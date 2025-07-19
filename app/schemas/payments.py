from pydantic import BaseModel
from datetime import datetime


class SCoursePaymentRequest(BaseModel):
    course_id: int
    currency: str = "RUB"
    card_token: str | None = None


class SPaymentResponse(BaseModel):
    status: str
    payment_intent_id: str
    transaction_id: int | None = None
    currency: str
    timestamp: datetime
    message: str | None = None
    course_id: int
