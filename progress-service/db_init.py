import logging
import time

from database import get_connection


logger = logging.getLogger("progress-service")


# Предметні таблиці сервісу відстеження прогресу (схема progress)
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS progress.tasks (
    task_id            INTEGER      PRIMARY KEY,
    user_id            INTEGER      NOT NULL,
    plan_id            INTEGER      NOT NULL,
    module_id          INTEGER      NULL,
    title              VARCHAR(200) NOT NULL,
    status             VARCHAR(20)  NOT NULL DEFAULT 'in_progress',
    status_updated_at  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    completed_at       TIMESTAMPTZ  NULL,
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT tasks_status_check
        CHECK (status IN ('in_progress', 'completed', 'postponed'))
);

CREATE INDEX IF NOT EXISTS tasks_user_idx   ON progress.tasks (user_id);
CREATE INDEX IF NOT EXISTS tasks_plan_idx   ON progress.tasks (plan_id);
CREATE INDEX IF NOT EXISTS tasks_module_idx ON progress.tasks (module_id);

CREATE TABLE IF NOT EXISTS progress.status_history (
    history_id   SERIAL       PRIMARY KEY,
    task_id      INTEGER      NOT NULL
                 REFERENCES progress.tasks (task_id) ON DELETE CASCADE,
    old_status   VARCHAR(20)  NULL,
    new_status   VARCHAR(20)  NOT NULL,
    changed_at   TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS status_history_task_idx
    ON progress.status_history (task_id);

CREATE TABLE IF NOT EXISTS progress.goals (
    goal_id       SERIAL       PRIMARY KEY,
    user_id       INTEGER      NOT NULL,
    title         VARCHAR(200) NOT NULL,
    plan_id       INTEGER      NULL,
    module_id     INTEGER      NULL,
    target_count  INTEGER      NOT NULL,
    start_date    DATE         NOT NULL DEFAULT CURRENT_DATE,
    end_date      DATE         NOT NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    CONSTRAINT goals_target_check CHECK (target_count > 0),
    CONSTRAINT goals_dates_check  CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS goals_user_idx ON progress.goals (user_id);
"""


# Створення таблиць під час запуску сервісу (з повторними спробами)
def init_db(attempts: int = 5, delay: int = 3) -> None:
    for attempt in range(1, attempts + 1):
        try:
            with get_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(SCHEMA_SQL)
            logger.info("Progress tables are ready")
            return
        except Exception as error:
            logger.warning(
                "Database init attempt %s/%s failed: %s",
                attempt, attempts, error
            )
            time.sleep(delay)

    logger.error("Progress tables were not created")
