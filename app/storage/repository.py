from sqlalchemy import select

from app.storage.database import SessionLocal
from app.storage.models import AgentEvent, TaskRecord


def create_task(task_id: str, student_id: str, message: str, mode: str = "agent") -> None:
    with SessionLocal.begin() as db:
        db.add(TaskRecord(id=task_id, student_id=student_id, message=message, mode=mode))


def add_event(task_id: str, event_type: str, message: str, details: dict | None = None) -> None:
    with SessionLocal.begin() as db:
        db.add(AgentEvent(task_id=task_id, event_type=event_type, message=message, details=details or {}))


def finish_task(task_id: str, status: str, response: str) -> None:
    with SessionLocal.begin() as db:
        task = db.get(TaskRecord, task_id)
        if task:
            task.status = status
            task.response = response


def get_task(task_id: str) -> dict | None:
    with SessionLocal() as db:
        task = db.get(TaskRecord, task_id)
        if not task:
            return None
        events = db.scalars(select(AgentEvent).where(AgentEvent.task_id == task_id).order_by(AgentEvent.id)).all()
        return {
            "task_id": task.id,
            "student_id": task.student_id,
            "message": task.message,
            "status": task.status,
            "response": task.response,
            "events": [{"type": e.event_type, "message": e.message, "details": e.details, "created_at": e.created_at} for e in events],
        }


def metric_rows() -> list[tuple[str, str]]:
    with SessionLocal() as db:
        tasks = db.scalars(select(TaskRecord)).all()
        return [(t.status, t.mode) for t in tasks]
