from datetime import date


# Прогрес (%) = завершені / усі × 100; якщо завдань немає — 0
def progress_percent(completed: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(completed / total * 100, 2)


# Досягнення цілі (%) = виконано / заплановано × 100, не більше 100
def achievement_percent(completed: int, target: int) -> float:
    if target <= 0:
        return 0.0
    return round(min(completed / target * 100, 100.0), 2)


# Стан цілі: досягнуто / триває / не досягнуто (строк минув)
def goal_status(completed: int, target: int, end_date: date, today: date | None = None) -> str:
    today = today or date.today()
    if completed >= target:
        return "achieved"
    if today <= end_date:
        return "in_progress"
    return "not_achieved"
