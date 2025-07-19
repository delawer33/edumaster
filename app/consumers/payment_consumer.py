import asyncio
import json
import aio_pika
from sqlalchemy import select

from app.db import get_async_db_session, CoursePurchase
from app.helpers import payments, obj_exist_check
from app.schemas import SCoursePaymentRequest
from app.core.rabbitmq import get_rabbitmq_connection


async def process_payment_request(message: aio_pika.IncomingMessage):
    async with message.process():
        try:
            payment_data = json.loads(message.body.decode())
            print(f" [x] Received {payment_data}")

            payment_intent_id = payment_data.get("payment_intent_id")
            course_id = payment_data.get("course_id")
            currency = payment_data.get("currency")
            card_token = payment_data.get("card_token")
            user_id = payment_data.get("user_id")

            async for db_session in get_async_db_session():
                repo = payments.PaymentRepository(db_session)

                stmt = select(CoursePurchase).where(
                    CoursePurchase.user_id == user_id,
                    CoursePurchase.course_id == course_id,
                )
                cp_check = await db_session.execute(stmt)
                cp_check_result = cp_check.scalars().first()

                if cp_check_result is not None:
                    print(
                        f" [!] Course {course_id} already purchased by user {user_id}. Creating duplicate transaction record for intent: {payment_intent_id}."
                    )

                    await repo.create_duplicate_transaction(
                        payment_intent_id=payment_intent_id,
                        user_id=user_id,
                        course_id=course_id,
                        currency=currency,
                        message="Курс уже приобретен: повторная попытка платежа.",
                    )
                    return

                payment_request_obj = SCoursePaymentRequest(
                    course_id=course_id,
                    currency=currency,
                    card_token=card_token,
                )

                course = await obj_exist_check.course_exists(
                    course_id, db_session
                )

                transaction = await repo.create_transaction(
                    payment_request_obj,
                    user_id=user_id,
                    payment_intent_id=payment_intent_id,
                )

                if not course:
                    print(
                        f" [!] Course {course_id} not found. Cannot process payment for intent {payment_intent_id}."
                    )
                    if transaction:
                        transaction.status = "failed"
                        transaction.message = (
                            "Course not found for payment intent."
                        )
                        db_session.add(transaction)
                        await db_session.commit()
                    return

                if transaction.status == "success":
                    cp = CoursePurchase(
                        user_id=user_id,
                        course_id=course.id,
                        transaction_id=transaction.id,
                    )
                    db_session.add(cp)
                    await db_session.commit()
                    print(
                        f" [✔] Payment for course {course_id} by user {user_id} processed successfully. Transaction ID: {transaction.id}, Intent ID: {payment_intent_id}"
                    )
                else:
                    print(
                        f" [✗] Transaction failed for course {course_id} by user {user_id}. Status: {transaction.status}, Intent ID: {payment_intent_id}"
                    )

        except json.JSONDecodeError:
            print(
                f" [!] Invalid JSON message for intent {payment_intent_id}: {message.body.decode()}"
            )
        except Exception as e:
            print(
                f" [!] Error processing message for intent {payment_intent_id}: {e}"
            )


async def main():
    connection = await get_rabbitmq_connection()
    async with connection:
        channel = await connection.channel()

        queue_name = "payment_requests_queue"
        queue = await channel.declare_queue(queue_name, durable=True)

        print(
            f" [*] Waiting for messages in {queue_name}. To exit press CTRL+C"
        )

        await queue.consume(process_payment_request)

        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            pass
        finally:
            print(" [*] Shutting down consumer.")


if __name__ == "__main__":
    asyncio.run(main())
