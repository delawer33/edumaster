from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import mapped_column, Mapped, relationship

from app.db import Base, aymentTransaction


class CoursePurchase(Base):
    __tablename__ = "course_purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id"), nullable=False
    )

    transaction_id: Mapped[int] = mapped_column(
        ForeignKey("payment_transactions.id"), nullable=False, unique=True
    )

    user = relationship(
        "User", foreign_keys=[user_id], back_populates="purchases"
    )

    course = relationship(
        "Course", foreign_keys=[course_id], back_populates="purchases"
    )

    transaction: Mapped["PaymentTransaction"] = relationship(
        "PaymentTransaction", uselist=False, back_populates="course_purchase"
    )
