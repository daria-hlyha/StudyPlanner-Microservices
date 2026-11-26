
from rabbitmq import get_rabbitmq_connection


def main():
    connection = None

    try:
        # Підключення до RabbitMQ
        connection = get_rabbitmq_connection()
        channel = connection.channel()

        # Параметри тестування
        queue_name = "auth_test"
        message = "Auth Service test message"

        # Створення тестової черги
        channel.queue_declare(queue=queue_name, durable=True)

        # Підтвердження публікації повідомлень брокером
        channel.confirm_delivery()

        # Надсилання повідомлення
        channel.basic_publish(
            exchange="",
            routing_key=queue_name,
            body=message.encode(),
            mandatory=True
        )

        print("Sent:", message)

        # Отримання повідомлення
        method, properties, body = channel.basic_get(
            queue=queue_name,
            auto_ack=False
        )

        # Перевірка наявності повідомлення
        if method is None:
            raise RuntimeError("No message received")

        received_message = body.decode()
        print("Received:", received_message)

        # Перевірка відповідності повідомлень
        if received_message != message:
            channel.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=True
            )
            raise RuntimeError("Messages do not match")

        # Підтвердження отримання
        channel.basic_ack(delivery_tag=method.delivery_tag)

        print("RabbitMQ test: PASSED")

    except Exception as error:
        print("RabbitMQ test: FAILED")
        print("Error:", error)
        raise SystemExit(1)

    finally:
        # Закриття з'єднання
        if connection is not None and connection.is_open:
            connection.close()


if __name__ == "__main__":
    main()
