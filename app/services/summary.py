from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app import models


def get_or_create_today(patient_id, db: Session) -> models.DailySummary:
    today = date.today()
    summary = (
        db.query(models.DailySummary)
        .filter(models.DailySummary.patient_id == patient_id, models.DailySummary.date == today)
        .first()
    )
    if summary is None:
        summary = models.DailySummary(patient_id=patient_id, date=today, app_used=True)
        db.add(summary)
        db.flush()
    return summary


def touch(
    patient_id,
    db: Session,
    *,
    app_used: Optional[bool] = None,
    cognitive_game_completed: Optional[bool] = None,
    mood_sleep_completed: Optional[bool] = None,
    movement_completed: Optional[bool] = None,
    medications_taken_delta: int = 0,
    medications_missed_delta: int = 0,
    tasks_completed_delta: int = 0,
    tasks_total_delta: int = 0,
    last_sync: Optional[datetime] = None,
) -> models.DailySummary:
    summary = get_or_create_today(patient_id, db)
    if app_used is not None:
        summary.app_used = summary.app_used or app_used
    if cognitive_game_completed is not None:
        summary.cognitive_game_completed = summary.cognitive_game_completed or cognitive_game_completed
    if mood_sleep_completed is not None:
        summary.mood_sleep_completed = summary.mood_sleep_completed or mood_sleep_completed
    if movement_completed is not None:
        summary.movement_completed = summary.movement_completed or movement_completed
    summary.medications_taken += medications_taken_delta
    summary.medications_missed += medications_missed_delta
    summary.tasks_completed += tasks_completed_delta
    summary.tasks_total += tasks_total_delta
    if last_sync is not None:
        summary.last_sync = last_sync
    db.flush()
    return summary
