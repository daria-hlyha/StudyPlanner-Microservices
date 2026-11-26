from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Response, status
from psycopg import errors
from psycopg.rows import dict_row

from database import get_connection
from events import publish_status_changed
from progress_calc import achievement_percent, goal_status, progress_percent
from schemas import (
    STATUS_LABELS,
    GoalCreate,
    GoalOut,
    ProgressOut,
    StatusChangeResult,
    StatusHistoryOut,
    StatusUpdate,
    TaskCreate,
    TaskOut,
    TaskStatus,
    UserSummaryOut,
)


router = APIRouter()

TASK_COLUMNS = """
    task_id, user_id, plan_id, module_id, title, status,
    status_updated_at, completed_at, created_at
"""


# ---------- Допоміжні функції ----------

def task_out(row: dict) -> dict:
    return {**row, "status_label": STATUS_LABELS[row["status"]]}


def get_task_or_404(cursor, task_id: int) -> dict:
    cursor.execute(
        f"SELECT {TASK_COLUMNS} FROM progress.tasks WHERE task_id = %s",
        (task_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Завдання не знайдено")
    return row


# Підрахунок завдань за статусами для плану, модуля або користувача
def count_progress(cursor, scope: str, scope_id: int, user_id: Optional[int] = None) -> dict:
    column = {"plan": "plan_id", "module": "module_id", "user": "user_id"}[scope]
    sql = f"""
        SELECT
            COUNT(*)                                        AS total_tasks,
            COUNT(*) FILTER (WHERE status = 'completed')    AS completed,
            COUNT(*) FILTER (WHERE status = 'in_progress')  AS in_progress,
            COUNT(*) FILTER (WHERE status = 'postponed')    AS postponed
        FROM progress.tasks
        WHERE {column} = %s
    """
    params = [scope_id]
    if user_id is not None:
        sql += " AND user_id = %s"
        params.append(user_id)

    cursor.execute(sql, params)
    row = cursor.fetchone()
    return {
        "scope": scope,
        "scope_id": scope_id,
        **row,
        "progress_percent": progress_percent(row["completed"], row["total_tasks"]),
    }


# Розрахунок досягнення навчальної цілі
def goal_out(cursor, goal: dict) -> dict:
    sql = """
        SELECT COUNT(*) AS completed_count
        FROM progress.tasks
        WHERE user_id = %s
          AND status = 'completed'
          AND completed_at::date BETWEEN %s AND %s
    """
    params = [goal["user_id"], goal["start_date"], goal["end_date"]]
    if goal["plan_id"] is not None:
        sql += " AND plan_id = %s"
        params.append(goal["plan_id"])
    if goal["module_id"] is not None:
        sql += " AND module_id = %s"
        params.append(goal["module_id"])

    cursor.execute(sql, params)
    completed = cursor.fetchone()["completed_count"]
    return {
        **goal,
        "completed_count": completed,
        "achievement_percent": achievement_percent(completed, goal["target_count"]),
        "goal_status": goal_status(completed, goal["target_count"], goal["end_date"]),
    }


# ---------- 1. Відстеження завдань і модулів ----------

@router.post(
    "/tasks",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Завдання"],
    summary="Додати завдання до відстеження",
)
def create_task(task: TaskCreate):
    try:
        with get_connection() as connection:
            with connection.cursor(row_factory=dict_row) as cursor:
                completed_at_sql = "now()" if task.status == "completed" else "NULL"
                cursor.execute(
                    f"""
                    INSERT INTO progress.tasks
                        (task_id, user_id, plan_id, module_id, title, status, completed_at)
                    VALUES (%s, %s, %s, %s, %s, %s, {completed_at_sql})
                    RETURNING {TASK_COLUMNS}
                    """,
                    (task.task_id, task.user_id, task.plan_id,
                     task.module_id, task.title, task.status),
                )
                row = cursor.fetchone()
                cursor.execute(
                    """
                    INSERT INTO progress.status_history (task_id, old_status, new_status)
                    VALUES (%s, NULL, %s)
                    """,
                    (row["task_id"], row["status"]),
                )
        return task_out(row)
    except errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Завдання з таким task_id вже відстежується")


@router.get(
    "/tasks",
    response_model=List[TaskOut],
    tags=["Завдання"],
    summary="Список завдань з фільтрацією",
)
def list_tasks(
    user_id: Optional[int] = Query(default=None, gt=0),
    plan_id: Optional[int] = Query(default=None, gt=0),
    module_id: Optional[int] = Query(default=None, gt=0),
    status_filter: Optional[TaskStatus] = Query(default=None, alias="status"),
):
    conditions, params = [], []
    for column, value in (("user_id", user_id), ("plan_id", plan_id),
                          ("module_id", module_id), ("status", status_filter)):
        if value is not None:
            conditions.append(f"{column} = %s")
            params.append(value)

    sql = f"SELECT {TASK_COLUMNS} FROM progress.tasks"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += " ORDER BY task_id"

    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(sql, params)
            return [task_out(row) for row in cursor.fetchall()]


@router.get(
    "/tasks/{task_id}",
    response_model=TaskOut,
    tags=["Завдання"],
    summary="Отримати завдання",
)
def get_task(task_id: int):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            return task_out(get_task_or_404(cursor, task_id))


@router.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Завдання"],
    summary="Прибрати завдання з відстеження",
)
def delete_task(task_id: int):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM progress.tasks WHERE task_id = %s", (task_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Завдання не знайдено")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- 3. Статуси завдань ----------

@router.patch(
    "/tasks/{task_id}/status",
    response_model=StatusChangeResult,
    tags=["Статуси"],
    summary="Змінити статус завдання та перерахувати прогрес",
)
def change_status(task_id: int, update: StatusUpdate):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            old = get_task_or_404(cursor, task_id)

            if old["status"] == update.status:
                row = old
            else:
                cursor.execute(
                    f"""
                    UPDATE progress.tasks
                    SET status = %s,
                        status_updated_at = now(),
                        completed_at = CASE WHEN %s THEN now() ELSE NULL END
                    WHERE task_id = %s
                    RETURNING {TASK_COLUMNS}
                    """,
                    (update.status, update.status == "completed", task_id),
                )
                row = cursor.fetchone()
                cursor.execute(
                    """
                    INSERT INTO progress.status_history (task_id, old_status, new_status)
                    VALUES (%s, %s, %s)
                    """,
                    (task_id, old["status"], update.status),
                )

            plan_progress = count_progress(cursor, "plan", row["plan_id"], row["user_id"])

    if old["status"] != update.status:
        publish_status_changed(row, old["status"], plan_progress["progress_percent"])

    return {"task": task_out(row), "plan_progress": plan_progress}


@router.get(
    "/tasks/{task_id}/history",
    response_model=List[StatusHistoryOut],
    tags=["Статуси"],
    summary="Історія змін статусу завдання",
)
def task_history(task_id: int):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            get_task_or_404(cursor, task_id)
            cursor.execute(
                """
                SELECT history_id, task_id, old_status, new_status, changed_at
                FROM progress.status_history
                WHERE task_id = %s
                ORDER BY changed_at, history_id
                """,
                (task_id,),
            )
            return cursor.fetchall()


# ---------- 2. Оцінка прогресу ----------

@router.get(
    "/progress/plans/{plan_id}",
    response_model=ProgressOut,
    tags=["Прогрес"],
    summary="Прогрес навчального плану",
)
def plan_progress(plan_id: int, user_id: Optional[int] = Query(default=None, gt=0)):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            return count_progress(cursor, "plan", plan_id, user_id)


@router.get(
    "/progress/plans/{plan_id}/modules",
    response_model=List[ProgressOut],
    tags=["Прогрес"],
    summary="Прогрес кожного модуля плану",
)
def plan_modules_progress(plan_id: int, user_id: Optional[int] = Query(default=None, gt=0)):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            sql = """
                SELECT DISTINCT module_id FROM progress.tasks
                WHERE plan_id = %s AND module_id IS NOT NULL
            """
            params = [plan_id]
            if user_id is not None:
                sql += " AND user_id = %s"
                params.append(user_id)
            cursor.execute(sql + " ORDER BY module_id", params)
            modules = [row["module_id"] for row in cursor.fetchall()]
            return [count_progress(cursor, "module", m, user_id) for m in modules]


@router.get(
    "/progress/modules/{module_id}",
    response_model=ProgressOut,
    tags=["Прогрес"],
    summary="Прогрес навчального модуля",
)
def module_progress(module_id: int, user_id: Optional[int] = Query(default=None, gt=0)):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            return count_progress(cursor, "module", module_id, user_id)


@router.get(
    "/progress/users/{user_id}",
    response_model=UserSummaryOut,
    tags=["Прогрес"],
    summary="Загальний прогрес користувача",
)
def user_summary(user_id: int):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            overall = count_progress(cursor, "user", user_id)

            cursor.execute(
                "SELECT DISTINCT plan_id FROM progress.tasks WHERE user_id = %s ORDER BY plan_id",
                (user_id,),
            )
            plans = [count_progress(cursor, "plan", r["plan_id"], user_id)
                     for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM progress.goals WHERE user_id = %s", (user_id,))
            goals = [goal_out(cursor, g) for g in cursor.fetchall()]

    return {
        "user_id": user_id,
        "overall": overall,
        "plans": plans,
        "goals_total": len(goals),
        "goals_achieved": sum(1 for g in goals if g["goal_status"] == "achieved"),
    }


# ---------- Навчальні цілі ----------

@router.post(
    "/goals",
    response_model=GoalOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Цілі"],
    summary="Створити навчальну ціль",
)
def create_goal(goal: GoalCreate):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                INSERT INTO progress.goals
                    (user_id, title, plan_id, module_id, target_count, start_date, end_date)
                VALUES (%s, %s, %s, %s, %s, COALESCE(%s::date, CURRENT_DATE), %s)
                RETURNING *
                """,
                (goal.user_id, goal.title, goal.plan_id, goal.module_id,
                 goal.target_count, goal.start_date, goal.end_date),
            )
            return goal_out(cursor, cursor.fetchone())


@router.get(
    "/goals",
    response_model=List[GoalOut],
    tags=["Цілі"],
    summary="Цілі користувача з відсотком досягнення",
)
def list_goals(user_id: int = Query(gt=0)):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                "SELECT * FROM progress.goals WHERE user_id = %s ORDER BY goal_id",
                (user_id,),
            )
            return [goal_out(cursor, g) for g in cursor.fetchall()]


@router.get(
    "/goals/{goal_id}",
    response_model=GoalOut,
    tags=["Цілі"],
    summary="Отримати ціль",
)
def get_goal(goal_id: int):
    with get_connection() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute("SELECT * FROM progress.goals WHERE goal_id = %s", (goal_id,))
            goal = cursor.fetchone()
            if goal is None:
                raise HTTPException(status_code=404, detail="Ціль не знайдено")
            return goal_out(cursor, goal)


@router.delete(
    "/goals/{goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Цілі"],
    summary="Видалити ціль",
)
def delete_goal(goal_id: int):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM progress.goals WHERE goal_id = %s", (goal_id,))
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Ціль не знайдено")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
