
import os
import pika


# Створення підключення до RabbitMQ
def get_rabbitmq_connection():

    # Облікові дані для підключення
    credentials = pika.PlainCredentials(
        os.environ["RABBITMQ_USER"],
        os.environ["RABBITMQ_PASSWORD"]
    )

    # Параметри підключення до брокера повідомлень
    parameters = pika.ConnectionParameters(
        host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
        port=int(os.getenv("RABBITMQ_PORT", "5672")),
        credentials=credentials,
        connection_attempts=3,
        retry_delay=2,
        socket_timeout=5,
        stack_timeout=10,
        blocked_connection_timeout=10
    )

    # Встановлення з'єднання
    connection = pika.BlockingConnection(parameters)

    return connection
