from rabbitmq import get_rabbitmq_connection

# Подключение к RabbitMQ
connection = get_rabbitmq_connection()
channel = connection.channel()

# Создание очереди
channel.queue_declare(queue="auth_test", durable=True)

# Отправка сообщения
message = "Auth Service test message"

channel.basic_publish(
    exchange="",
    routing_key="auth_test",
    body=message.encode()
)

print("Sent:", message)

# Получение сообщения
method, properties, body = channel.basic_get(
    queue="auth_test",
    auto_ack=False
)

if method is not None:
    received_message = body.decode()
    print("Received:", received_message)

    channel.basic_ack(delivery_tag=method.delivery_tag)
else:
    print("No message received")


connection.close()