from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, assert_can_access_patient
from app.services import summary as summary_service
from app.services import alerts as alerts_service

router = APIRouter(tags=["mood-sleep"])

UNCERTAIN_STREAK_FOR_ALERT = 3


@router.post("/patients/{patient_id}/mood-sleep", response_model=schemas.MoodSleepOut, status_code=status.HTTP_201_CREATED)
def submit_mood_sleep(
    patient_id: str,
    body: schemas.MoodSleepCreate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The morning 'how did you sleep? how are you feeling?' check-in. One
    entry per patient per day - resubmitting today just updates it."""
    assert_can_access_patient(patient_id, user, db)
    today = date.today()
    entry = (
        db.query(models.MoodSleepLog)
        .filter(models.MoodSleepLog.patient_id == patient_id, models.MoodSleepLog.date == today)
        .first()
    )
    if entry is None:
        entry = models.MoodSleepLog(patient_id=patient_id, date=today)
        db.add(entry)

    entry.sleep_quality = body.sleep_quality
    entry.mood = body.mood
    entry.notes = body.notes
    db.flush()

    summary_service.touch(patient_id, db, mood_sleep_completed=True)

    if body.mood in ("anxious", "sad"):
        recent = (
            db.query(models.MoodSleepLog)
            .filter(models.MoodSleepLog.patient_id == patient_id)
            .order_by(models.MoodSleepLog.date.desc())
            .limit(UNCERTAIN_STREAK_FOR_ALERT)
            .all()
        )
        if len(recent) == UNCERTAIN_STREAK_FOR_ALERT and all(r.mood in ("anxious", "sad") for r in recent):
            patient_user = db.query(models.User).filter(models.User.user_id == patient_id).first()
            alerts_service.alert_repeated_uncertainty(patient_id, patient_user.name, db, UNCERTAIN_STREAK_FOR_ALERT)

    db.commit()
    db.refresh(entry)
    return entry


@router.get("/patients/{patient_id}/mood-sleep", response_model=List[schemas.MoodSleepOut])
def mood_sleep_history(
    patient_id: str,
    days: int = 14,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assert_can_access_patient(patient_id, user, db)
    since = date.today() - timedelta(days=days)
    rows = (
        db.query(models.MoodSleepLog)
        .filter(models.MoodSleepLog.patient_id == patient_id, models.MoodSleepLog.date >= since)
        .order_by(models.MoodSleepLog.date.desc())
        .all()
    )
    return rows
