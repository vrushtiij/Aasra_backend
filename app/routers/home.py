from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, assert_can_access_patient
from app.services import summary as summary_service

router = APIRouter(tags=["home"])


class HomeResponse(BaseModel):
    patient_name: str
    greeting: str
    mood_sleep_check_needed: bool
    cognitive_game_done_today: bool
    todays_medications: list[schemas.MedicationLogOut]
    todays_reminders: list[schemas.ReminderOut]


@router.get("/patients/{patient_id}/home", response_model=HomeResponse)
def get_home(
    patient_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The first screen when the patient opens the app: greeting by name,
    whether the mood/sleep question still needs answering, whether today's
    one short cognitive game is done yet, and today's schedule."""
    assert_can_access_patient(patient_id, user, db)
    patient_user = db.query(models.User).filter(models.User.user_id == patient_id).first()
    today = date.today()

    mood_entry = (
        db.query(models.MoodSleepLog)
        .filter(models.MoodSleepLog.patient_id == patient_id, models.MoodSleepLog.date == today)
        .first()
    )
    summary = (
        db.query(models.DailySummary)
        .filter(models.DailySummary.patient_id == patient_id, models.DailySummary.date == today)
        .first()
    )

    hour = datetime.now().hour
    time_of_day = "morning" if hour < 12 else "afternoon" if hour < 17 else "evening"
    greeting = f"Good {time_of_day}, {patient_user.name}!"

    day_start = datetime.combine(today, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    meds = (
        db.query(models.MedicationLog)
        .filter(
            models.MedicationLog.patient_id == patient_id,
            models.MedicationLog.scheduled_time >= day_start,
            models.MedicationLog.scheduled_time < day_end,
        )
        .order_by(models.MedicationLog.scheduled_time)
        .all()
    )
    reminders = (
        db.query(models.Reminder)
        .filter(models.Reminder.patient_id == patient_id, models.Reminder.date == today)
        .order_by(models.Reminder.time)
        .all()
    )

    summary_service.touch(patient_id, db, app_used=True)
    db.commit()

    return HomeResponse(
        patient_name=patient_user.name,
        greeting=greeting,
        mood_sleep_check_needed=mood_entry is None,
        cognitive_game_done_today=bool(summary.cognitive_game_completed) if summary else False,
        todays_medications=meds,
        todays_reminders=reminders,
    )
