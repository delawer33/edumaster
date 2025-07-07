from pydantic import BaseModel
from datetime import datetime


class SCoursePaymentRequest(BaseModel):
    course_id: int
    currency: str = "RUB"
    card_token: str | None = None


class SPaymentResponse(BaseModel):
    status: str
    transaction_id: int
    currency: str
    timestamp: datetime
    message: str
    course_id: int
