import json
import logging
from datetime import datetime, timezone

import pika

from rabbitmq import get_rabbitmq_connection


logger = logging.getLogger("progress-service")

# Обмінник (exchange) подій сервісу відстеження прогресу.
# Тип fanout: кожен сервіс, якому потрібні ці події (наприклад, сервіс персоналізації),
# підключає до нього власну чергу. Без підключених черг повідомлення не накопичуються.
PROGRESS_EVENTS_EXCHANGE = "progress_events"


# Публікація події про зміну статусу завдання.
# Помилка брокера не повинна скасовувати зміну статусу, тому лише записується в журнал.
def publish_status_changed(task: dict, old_status: str | None, plan_progress: float) -> bool:
    event = {
        "event": "task_status_changed",
        "task_id": task["task_id"],
        "user_id": task["user_id"],
        "plan_id": task["plan_id"],
        "module_id": task["module_id"],
        "old_status": old_status,
        "new_status": task["status"],
        "plan_progress_percent": plan_progress,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }

    connection = None
    try:
        connection = get_rabbitmq_connection()
        channel = connection.channel()
        channel.exchange_declare(
            exchange=PROGRESS_EVENTS_EXCHANGE,
            exchange_type="fanout",
            durable=True,
        )
        channel.basic_publish(
            exchange=PROGRESS_EVENTS_EXCHANGE,
            routing_key="",
            body=json.dumps(event, ensure_ascii=False).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )
        return True
    except Exception as error:
        logger.warning("Event was not published: %s", error)
        return False
    finally:
        if connection is not None and connection.is_open:
            connection.close()
