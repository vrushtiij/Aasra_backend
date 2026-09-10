from datetime import date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, require_caretaker, assert_can_access_patient
from app.services import summary as summary_service

router = APIRouter(tags=["reminders"])


@router.post("/patients/{patient_id}/reminders", response_model=schemas.ReminderOut, status_code=status.HTTP_201_CREATED)
def create_reminder(
    patient_id: str,
    body: schemas.ReminderCreate,
    caretaker: models.User = Depends(require_caretaker),
    db: Session = Depends(get_db),
):
    assert_can_access_patient(patient_id, caretaker, db)
    reminder = models.Reminder(
        patient_id=patient_id,
        title=body.title,
        description=body.description,
        reminder_type=body.reminder_type,
        date=body.date,
        time=body.time,
        repeat_pattern=body.repeat_pattern or "once",
        created_by=caretaker.user_id,
    )
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return reminder


@router.get(
    "/patients/{patient_id}/reminders/today",
    response_model=List[schemas.ReminderOut]
)
def todays_reminders(
    patient_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    print("SCHEMAS FILE:", schemas.__file__)
    print("REMINDER OUT:", schemas.ReminderOut.model_fields)
    assert_can_access_patient(patient_id, user, db)

    reminders = (
        db.query(models.Reminder)
        .filter(models.Reminder.patient_id == patient_id)
        .order_by(models.Reminder.time)
        .all()
    )

    print("REMINDERS FOUND:", len(reminders))
    print("REMINDER DATA:", reminders)

    return reminders


@router.put("/reminders/{reminder_id}/status", response_model=schemas.ReminderOut)
def update_reminder_status(
    reminder_id: str,
    body: schemas.ReminderStatusUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Patient taps Done / Not Yet on a task, meal, or appointment reminder."""
    reminder = db.query(models.Reminder).filter(models.Reminder.reminder_id == reminder_id).first()
    if reminder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reminder not found")
    assert_can_access_patient(reminder.patient_id, user, db)

    if body.status not in ("completed", "missed", "dismissed"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "status must be completed, missed or dismissed")

    was_pending = reminder.status == "pending"
    reminder.status = body.status
    db.commit()
    db.refresh(reminder)

    if was_pending:
        summary_service.touch(
            reminder.patient_id, db,
            tasks_completed_delta=1 if body.status == "completed" else 0,
            tasks_total_delta=1,
        )
        db.commit()

    return reminder


@router.delete("/reminders/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(
    reminder_id: str,
    caretaker: models.User = Depends(require_caretaker),
    db: Session = Depends(get_db),
):
    reminder = db.query(models.Reminder).filter(models.Reminder.reminder_id == reminder_id).first()
    if reminder is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reminder not found")
    assert_can_access_patient(reminder.patient_id, caretaker, db)
    db.delete(reminder)
    db.commit()
