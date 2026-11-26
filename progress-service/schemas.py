from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


# Допустимі статуси навчальних завдань
TaskStatus = Literal["in_progress", "completed", "postponed"]

STATUS_LABELS = {
    "in_progress": "У процесі",
    "completed": "Завершено",
    "postponed": "Відкладено",
}


# ---------- Завдання ----------

class TaskCreate(BaseModel):
    task_id: int = Field(gt=0, description="Ідентифікатор завдання з Study Plan Service")
    user_id: int = Field(gt=0, description="Ідентифікатор власника завдання")
    plan_id: int = Field(gt=0, description="Ідентифікатор навчального плану")
    module_id: Optional[int] = Field(default=None, gt=0, description="Ідентифікатор навчального модуля")
    title: str = Field(min_length=1, max_length=200, description="Назва завдання")
    status: TaskStatus = Field(default="in_progress", description="Початковий статус")

    model_config = {
        "json_schema_extra": {
            "example": {
                "task_id": 1,
                "user_id": 1,
                "plan_id": 1,
                "module_id": 1,
                "title": "Підготувати конспект лекції 1",
                "status": "in_progress",
            }
        }
    }


class StatusUpdate(BaseModel):
    status: TaskStatus = Field(description="in_progress | completed | postponed")

    model_config = {"json_schema_extra": {"example": {"status": "completed"}}}


class TaskOut(BaseModel):
    task_id: int
    user_id: int
    plan_id: int
    module_id: Optional[int]
    title: str
    status: TaskStatus
    status_label: str
    status_updated_at: datetime
    completed_at: Optional[datetime]
    created_at: datetime


class StatusHistoryOut(BaseModel):
    history_id: int
    task_id: int
    old_status: Optional[str]
    new_status: str
    changed_at: datetime


# ---------- Прогрес ----------

class ProgressOut(BaseModel):
    scope: str
    scope_id: int
    total_tasks: int
    completed: int
    in_progress: int
    postponed: int
    progress_percent: float


class StatusChangeResult(BaseModel):
    task: TaskOut
    plan_progress: ProgressOut


# ---------- Навчальні цілі ----------

class GoalCreate(BaseModel):
    user_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    plan_id: Optional[int] = Field(default=None, gt=0, description="Ціль лише для одного плану")
    module_id: Optional[int] = Field(default=None, gt=0, description="Ціль лише для одного модуля")
    target_count: int = Field(gt=0, le=10000, description="Скільки завдань потрібно завершити")
    start_date: Optional[date] = Field(default=None, description="За замовчуванням — сьогодні")
    end_date: date

    @model_validator(mode="after")
    def check_dates(self):
        start = self.start_date or date.today()
        if self.end_date < start:
            raise ValueError("end_date не може бути раніше за start_date")
        return self

    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": 1,
                "title": "Виконати 10 завдань за тиждень",
                "plan_id": 1,
                "target_count": 10,
                "start_date": "2026-11-23",
                "end_date": "2026-11-30",
            }
        }
    }


class GoalOut(BaseModel):
    goal_id: int
    user_id: int
    title: str
    plan_id: Optional[int]
    module_id: Optional[int]
    target_count: int
    start_date: date
    end_date: date
    completed_count: int
    achievement_percent: float
    goal_status: Literal["achieved", "in_progress", "not_achieved"]
    created_at: datetime


class UserSummaryOut(BaseModel):
    user_id: int
    overall: ProgressOut
    plans: List[ProgressOut]
    goals_total: int
    goals_achieved: int
