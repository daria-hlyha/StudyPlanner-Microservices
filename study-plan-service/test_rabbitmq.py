from rabbitmq import get_rabbitmq_connection

# Підключення до RabbitMQ
connection = get_rabbitmq_connection()
channel = connection.channel()

# Створення черги
channel.queue_declare(queue="study_plan_test", durable=True)

# Надсилання повідомлення
message = "Study Plan Service test message"

channel.basic_publish(
    exchange="",
    routing_key="study_plan_test",
    body=message.encode()
)

print("Sent:", message)

# Отримання повідомлення
method, properties, body = channel.basic_get(
    queue="study_plan_test",
    auto_ack=False
)

if method is not None:
    received_message = body.decode()
    print("Received:", received_message)

    channel.basic_ack(delivery_tag=method.delivery_tag)
else:
    print("No message received")

# Закриття з'єднання
connection.close()
