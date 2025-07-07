from sqlalchemy import String, Float, Integer, DateTime, Uuid, ForeignKey, func
from sqlalchemy.orm import relationship, Mapped, mapped_column
from datetime import datetime
import uuid

from .user import User
from .base import Base


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    transaction_uuid: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        unique=True, index=True,
        default=lambda: str(uuid.uuid4())
    )
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    status: Mapped[str] = mapped_column(String(20), default="pending")
    card_token: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    message: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="payments")

    course_purchase: Mapped["CoursePurchase"] = relationship(
        "CoursePurchase",
        back_populates="transaction",
        uselist=False
    )

    def __repr__(self):
        return f"<PaymentTransaction {self.transaction_id} ({self.status})>"
