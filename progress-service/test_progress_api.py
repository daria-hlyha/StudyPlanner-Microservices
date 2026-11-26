import json
import sys
import urllib.error
import urllib.request
from datetime import date, timedelta


# Тестування REST API сервісу відстеження прогресу.
# Запуск: docker compose exec progress-service python test_progress_api.py
BASE_URL = "http://localhost:8000"

# Тестові ідентифікатори, щоб не перетинатися з реальними даними
USER_ID = 900001
PLAN_ID = 900001
MODULE_A = 900001
MODULE_B = 900002
TASK_IDS = list(range(900001, 900011))


def request(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as error:
        raw = error.read()
        return error.code, (json.loads(raw) if raw else None)


def check(name, condition):
    print(("OK    " if condition else "FAIL  ") + name)
    if not condition:
        raise AssertionError(name)


def cleanup():
    for task_id in TASK_IDS:
        request("DELETE", f"/tasks/{task_id}")
    _, goals = request("GET", f"/goals?user_id={USER_ID}")
    for goal in goals or []:
        request("DELETE", f"/goals/{goal['goal_id']}")


def main():
    cleanup()
    try:
        # 1. Відстеження завдань: 10 завдань у двох модулях
        for i, task_id in enumerate(TASK_IDS):
            code, _ = request("POST", "/tasks", {
                "task_id": task_id,
                "user_id": USER_ID,
                "plan_id": PLAN_ID,
                "module_id": MODULE_A if i < 5 else MODULE_B,
                "title": f"Тестове завдання {i + 1}",
            })
            check(f"створення завдання {task_id} -> 201", code == 201)

        code, _ = request("POST", "/tasks", {
            "task_id": TASK_IDS[0], "user_id": USER_ID,
            "plan_id": PLAN_ID, "title": "Дублікат",
        })
        check("повторне створення -> 409", code == 409)

        # Порожній план -> 0 %
        code, body = request("GET", "/progress/plans/999999999")
        check("план без завдань -> 0 %", code == 200 and body["progress_percent"] == 0)

        # 3. Статуси: 6 завершено, 1 відкладено
        for task_id in TASK_IDS[:6]:
            code, body = request("PATCH", f"/tasks/{task_id}/status", {"status": "completed"})
            check(f"статус {task_id} -> completed", code == 200
                  and body["task"]["completed_at"] is not None)
        code, _ = request("PATCH", f"/tasks/{TASK_IDS[6]}/status", {"status": "postponed"})
        check("статус -> postponed", code == 200)

        code, _ = request("PATCH", f"/tasks/{TASK_IDS[7]}/status", {"status": "done"})
        check("неприпустимий статус -> 422", code == 422)

        code, _ = request("PATCH", "/tasks/999999999/status", {"status": "completed"})
        check("неіснуюче завдання -> 404", code == 404)

        # Виправлення помилково встановленого статусу
        code, body = request("PATCH", f"/tasks/{TASK_IDS[5]}/status", {"status": "in_progress"})
        check("виправлення статусу: completed_at очищено", code == 200
              and body["task"]["completed_at"] is None)

        code, body = request("GET", f"/tasks/{TASK_IDS[5]}/history")
        check("історія статусів містить 3 записи", code == 200 and len(body) == 3)

        # Фільтрація за статусом
        code, body = request("GET", f"/tasks?user_id={USER_ID}&status=completed")
        check("фільтр completed -> 5 завдань", code == 200 and len(body) == 5)

        # 2. Прогрес плану: 5 із 10 = 50 %
        code, body = request("GET", f"/progress/plans/{PLAN_ID}?user_id={USER_ID}")
        check("прогрес плану = 50 %", code == 200 and body["progress_percent"] == 50.0
              and body["completed"] == 5 and body["postponed"] == 1)

        code, body = request("GET", f"/progress/modules/{MODULE_A}")
        check("прогрес модуля A = 100 %", code == 200 and body["progress_percent"] == 100.0)

        code, body = request("GET", f"/progress/plans/{PLAN_ID}/modules")
        check("прогрес за модулями: 2 модулі", code == 200 and len(body) == 2)

        # Навчальна ціль: 10 завершених за тиждень, виконано 5 -> 50 %
        today = date.today()
        code, goal = request("POST", "/goals", {
            "user_id": USER_ID,
            "title": "Виконати 10 завдань за тиждень",
            "plan_id": PLAN_ID,
            "target_count": 10,
            "start_date": today.isoformat(),
            "end_date": (today + timedelta(days=7)).isoformat(),
        })
        check("створення цілі -> 201, досягнення 50 %", code == 201
              and goal["achievement_percent"] == 50.0
              and goal["goal_status"] == "in_progress")

        code, _ = request("POST", "/goals", {
            "user_id": USER_ID, "title": "Помилкові дати", "target_count": 5,
            "start_date": "2026-12-31", "end_date": "2026-01-01",
        })
        check("ціль з помилковими датами -> 422", code == 422)

        code, body = request("GET", f"/progress/users/{USER_ID}")
        check("загальний прогрес користувача", code == 200
              and body["overall"]["total_tasks"] == 10 and body["goals_total"] == 1)

        print("Progress API test: PASSED")

    except AssertionError:
        print("Progress API test: FAILED")
        sys.exit(1)

    finally:
        cleanup()


if __name__ == "__main__":
    main()
