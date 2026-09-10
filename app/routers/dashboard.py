from datetime import date, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, require_caretaker, assert_can_access_patient
from app.services import alerts as alerts_service

router = APIRouter(tags=["dashboard"])


@router.get("/patients/{patient_id}/day-status", response_model=schemas.PatientDayStatus)
def get_day_status(
    patient_id: str,
    day: date = None,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """What the caregiver sees when they open a patient's profile: did they
    use the app, complete the cognitive activity, acknowledge medicines,
    finish tasks, answer mood/sleep, do movement, and when they last synced."""
    assert_can_access_patient(patient_id, user, db)
    day = day or date.today()
    summary = (
        db.query(models.DailySummary)
        .filter(models.DailySummary.patient_id == patient_id, models.DailySummary.date == day)
        .first()
    )
    meds_total = (
        db.query(models.MedicationLog)
        .join(models.MedicationSchedule, models.MedicationSchedule.schedule_id == models.MedicationLog.schedule_id)
        .join(models.Medication, models.Medication.medication_id == models.MedicationSchedule.medication_id)
        .filter(models.Medication.patient_id == patient_id)
        .count()
    )
    if summary is None:
        return schemas.PatientDayStatus(
            patient_id=patient_id, date=day, app_used=False, cognitive_game_completed=False,
            mood_sleep_completed=False, movement_completed=False, medications_taken=0,
            medications_missed=0, medications_total=meds_total, tasks_completed=0, tasks_total=0,
            last_sync=None, trend=None,
        )

    progress = (
        db.query(models.CognitiveProgress)
        .filter(models.CognitiveProgress.patient_id == patient_id, models.CognitiveProgress.date == day)
        .first()
    )
    return schemas.PatientDayStatus(
        patient_id=patient_id, date=day, app_used=summary.app_used,
        cognitive_game_completed=summary.cognitive_game_completed,
        mood_sleep_completed=summary.mood_sleep_completed,
        movement_completed=summary.movement_completed,
        medications_taken=summary.medications_taken,
        medications_missed=summary.medications_missed,
        medications_total=meds_total,
        tasks_completed=summary.tasks_completed,
        tasks_total=summary.tasks_total,
        last_sync=summary.last_sync,
        trend=progress.trend if progress else None,
    )


@router.get("/patients/{patient_id}/day-status/history", response_model=List[schemas.PatientDayStatus])
def day_status_history(
    patient_id: str,
    days: int = 7,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assert_can_access_patient(patient_id, user, db)
    since = date.today() - timedelta(days=days)
    summaries = (
        db.query(models.DailySummary)
        .filter(models.DailySummary.patient_id == patient_id, models.DailySummary.date >= since)
        .order_by(models.DailySummary.date)
        .all()
    )
    meds_total = (
        db.query(models.MedicationLog)
        .join(models.MedicationSchedule, models.MedicationSchedule.schedule_id == models.MedicationLog.schedule_id)
        .join(models.Medication, models.Medication.medication_id == models.MedicationSchedule.medication_id)
        .filter(models.Medication.patient_id == patient_id)
        .count()
    )
    out = []
    for s in summaries:
        progress = (
            db.query(models.CognitiveProgress)
            .filter(models.CognitiveProgress.patient_id == patient_id, models.CognitiveProgress.date == s.date)
            .first()
        )
        out.append(schemas.PatientDayStatus(
            patient_id=patient_id, date=s.date, app_used=s.app_used,
            cognitive_game_completed=s.cognitive_game_completed,
            mood_sleep_completed=s.mood_sleep_completed,
            movement_completed=s.movement_completed,
            medications_taken=s.medications_taken, medications_missed=s.medications_missed,
            medications_total=meds_total, tasks_completed=s.tasks_completed, tasks_total=s.tasks_total,
            last_sync=s.last_sync, trend=progress.trend if progress else None,
        ))
    return out


@router.get("/patients/{patient_id}/alerts", response_model=List[schemas.AlertOut])
def get_alerts(
    patient_id: str,
    caretaker: models.User = Depends(require_caretaker),
    db: Session = Depends(get_db),
):
    """Stronger alerts that need attention: repeated missed medicine, no
    activity by a certain time, repeated uncertainty, incomplete daily
    activity, or an open emergency. Computed on the fly."""
    assert_can_access_patient(patient_id, caretaker, db)
    patient_user = db.query(models.User).filter(models.User.user_id == patient_id).first()
    return alerts_service.compute_open_alerts(patient_id, patient_user.name, db)


@router.post("/patients/{patient_id}/generate-summary", response_model=schemas.PatientDayStatus)
def generate_summary(
    patient_id: str,
    caretaker: models.User = Depends(require_caretaker),
    db: Session = Depends(get_db),
):
    """End-of-day trigger (call from a scheduled job, or manually): pushes a
    normal 'summary ready' notification to caretakers. The daily_summaries
    row itself is already kept live throughout the day by the other
    endpoints, so this just surfaces it."""
    assert_can_access_patient(patient_id, caretaker, db)
    patient_user = db.query(models.User).filter(models.User.user_id == patient_id).first()
    if patient_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")

    alerts_service.notify_summary_ready(patient_id, patient_user.name, db)
    db.commit()
    return get_day_status(patient_id, None, caretaker, db)
