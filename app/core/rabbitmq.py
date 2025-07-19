import aio_pika
import json
import asyncio
from app.core import settings


async def get_rabbitmq_connection():
    connection_url = (
        f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASS}"
        f"@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/"
    )

    retries = 5
    delay = 5
    for i in range(retries):
        try:
            print(
                f"Attempting to connect to RabbitMQ (attempt {i+1}/{retries})..."
            )
            connection = await aio_pika.connect_robust(connection_url)
            print("Successfully connected to RabbitMQ!")
            return connection
        except aio_pika.exceptions.AMQPConnectionError as e:
            print(f"Connection to RabbitMQ failed: {e}")
            if i < retries - 1:
                print(f"Retrying in {delay} seconds...")
                await asyncio.sleep(delay)
            else:
                print("Max retries reached. Could not connect to RabbitMQ.")
                raise

    return None


async def publish_message(queue_name: str, message: dict):
    connection = None
    try:
        connection = await get_rabbitmq_connection()
        async with connection:
            channel = await connection.channel()
            await channel.declare_queue(queue_name, durable=True)

            await channel.default_exchange.publish(
                aio_pika.Message(body=json.dumps(message).encode()),
                routing_key=queue_name,
            )
            print(f" [x] Sent '{message}' to queue '{queue_name}'")
    except Exception as e:
        print(f"Error publishing message: {e}")
    finally:
        if connection and not connection.is_closed:
            await connection.close()
