
"""
Підключення до брокера повідомлень Study Plan Service.

Модуль забезпечує створення підключень до RabbitMQ
на основі централізованої конфігурації мікросервісу.
"""

import pika

from config import get_settings


# ==========================================================
# 1. СТВОРЕННЯ ПІДКЛЮЧЕННЯ ДО RABBITMQ
# ==========================================================

def get_rabbitmq_connection() -> pika.BlockingConnection:

    """Створення підключення до брокера повідомлень RabbitMQ."""

    # Отримання централізованої конфігурації
    settings = get_settings()

    # Облікові дані для підключення
    credentials = pika.PlainCredentials(
        username=settings.rabbitmq_user,
        password=settings.rabbitmq_password.get_secret_value()
    )

    # Параметри підключення до брокера повідомлень
    parameters = pika.ConnectionParameters(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        credentials=credentials,
        connection_attempts=settings.rabbitmq_connection_attempts,
        retry_delay=settings.rabbitmq_retry_delay,
        socket_timeout=settings.rabbitmq_socket_timeout,
        stack_timeout=settings.rabbitmq_stack_timeout,
        blocked_connection_timeout=settings.rabbitmq_blocked_connection_timeout
    )

    # Встановлення з'єднання
    connection = pika.BlockingConnection(parameters)

    return connection
