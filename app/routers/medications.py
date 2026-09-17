from datetime import date, datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, require_caretaker, assert_can_access_patient
from app.services import summary as summary_service
from app.services import alerts as alerts_service

router = APIRouter(tags=["medications"])


@router.post("/patients/{patient_id}/medications", response_model=schemas.MedicationOut, status_code=status.HTTP_201_CREATED)
def create_medication(
    patient_id: str,
    body: schemas.MedicationCreate,
    caretaker: models.User = Depends(require_caretaker),
    db: Session = Depends(get_db),
):
    assert_can_access_patient(patient_id, caretaker, db)
    med = models.Medication(
        patient_id=patient_id,
        medicine_name=body.medicine_name,
        dosage=body.dosage,
        quantity=body.quantity,
        frequency=body.frequency,
        start_date=body.start_date,
        end_date=body.end_date,
        instructions=body.instructions,
        prescribed_by=caretaker.user_id,
    )
    db.add(med)
    db.flush()

    for t in body.times:
        db.add(models.MedicationSchedule(
            medication_id=med.medication_id,
            time=t,
            days=body.days or "daily",
            grace_period=body.grace_period or 30,
        ))
    db.commit()
    db.refresh(med)
    return _to_medication_out(med, db)


@router.get("/patients/{patient_id}/medications", response_model=List[schemas.MedicationOut])
def list_medications(
    patient_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assert_can_access_patient(patient_id, user, db)
    meds = db.query(models.Medication).filter(models.Medication.patient_id == patient_id).all()
    return [_to_medication_out(m, db) for m in meds]


@router.put("/medications/{medication_id}", response_model=schemas.MedicationOut)
def update_medication(
    medication_id: str,
    body: schemas.MedicationCreate,
    caretaker: models.User = Depends(require_caretaker),
    db: Session = Depends(get_db),
):
    med = db.query(models.Medication).filter(models.Medication.medication_id == medication_id).first()
    if med is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Medication not found")
    assert_can_access_patient(med.patient_id, caretaker, db)

    for field in ("medicine_name", "dosage", "quantity", "frequency", "start_date", "end_date", "instructions"):
        setattr(med, field, getattr(body, field))
    db.commit()
    db.refresh(med)
    return _to_medication_out(med, db)


@router.delete("/medications/{medication_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_medication(
    medication_id: str,
    caretaker: models.User = Depends(require_caretaker),
    db: Session = Depends(get_db),
):
    med = db.query(models.Medication).filter(models.Medication.medication_id == medication_id).first()
    if med is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Medication not found")
    assert_can_access_patient(med.patient_id, caretaker, db)
    med.status = "completed"
    db.commit()


@router.get("/patients/{patient_id}/medication-logs/today", response_model=List[schemas.MedicationLogOut])
def todays_medication_logs(
    patient_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The 'Taken / Not Taken' prompts due today, generating any that don't
    exist yet for schedules whose time has arrived."""
    assert_can_access_patient(patient_id, user, db)
    _ensure_today_logs_exist(patient_id, db)
    day_start = datetime.combine(date.today(), datetime.min.time())
    day_end = day_start + timedelta(days=1)
    logs = (
        db.query(models.MedicationLog)
        .filter(
            models.MedicationLog.patient_id == patient_id,
            models.MedicationLog.scheduled_time >= day_start,
            models.MedicationLog.scheduled_time < day_end,
        )
        .order_by(models.MedicationLog.scheduled_time)
        .all()
    )
    return logs


@router.post("/medication-logs/{log_id}/action", response_model=schemas.MedicationLogOut)
def act_on_medication_log(
    log_id: str,
    body: schemas.MedicationLogActionRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Patient taps Taken/Not Taken (or a caregiver confirms on their behalf)."""
    log = db.query(models.MedicationLog).filter(models.MedicationLog.log_id == log_id).first()
    if log is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Log not found")
    assert_can_access_patient(log.patient_id, user, db)

    if body.status not in ("taken", "missed", "skipped"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "status must be taken, missed or skipped")

    log.status = body.status
    log.action_time = datetime.now()
    log.confirmed_by = user.user_id
    log.confirmation_method = body.confirmation_method or "app"
    db.flush()

    patient_user = db.query(models.User).filter(models.User.user_id == log.patient_id).first()
    if body.status == "taken":
        summary_service.touch(log.patient_id, db, medications_taken_delta=1)
    else:
        summary_service.touch(log.patient_id, db, medications_missed_delta=1)
        alerts_service.check_and_alert_missed_medication(log, patient_user.name, db)

    db.commit()
    db.refresh(log)
    return log


@router.post("/medication-logs/{log_id}/repeat", response_model=schemas.MedicationLogOut)
def repeat_medication_reminder(
    log_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Call this when a reminder was shown and ignored, so it gets re-shown
    later. Also marks it missed and alerts once it's been repeated too many times."""
    log = db.query(models.MedicationLog).filter(models.MedicationLog.log_id == log_id).first()
    if log is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Log not found")
    assert_can_access_patient(log.patient_id, user, db)

    log.reminder_count += 1
    if log.status == "unknown":
        log.status = "missed"
    db.flush()

    patient_user = db.query(models.User).filter(models.User.user_id == log.patient_id).first()
    alerts_service.check_and_alert_missed_medication(log, patient_user.name, db)

    db.commit()
    db.refresh(log)
    return log


def _ensure_today_logs_exist(patient_id: str, db: Session):
    """Lazily materializes today's medication_logs from active
    medication_schedule rows, so the client doesn't need a separate cron."""
    today = date.today()
    schedules = (
        db.query(models.MedicationSchedule)
        .join(models.Medication, models.Medication.medication_id == models.MedicationSchedule.medication_id)
        .filter(models.Medication.patient_id == patient_id, models.Medication.status == "active")
        .all()
    )
    for sched in schedules:
        scheduled_dt = datetime.combine(today, sched.time)
        exists = (
            db.query(models.MedicationLog)
            .filter(models.MedicationLog.schedule_id == sched.schedule_id, models.MedicationLog.scheduled_time == scheduled_dt)
            .first()
        )
        if not exists:
            db.add(models.MedicationLog(
                schedule_id=sched.schedule_id,
                patient_id=patient_id,
                scheduled_time=scheduled_dt,
                status="unknown",
            ))
    db.commit()


def _to_medication_out(med: models.Medication, db: Session) -> schemas.MedicationOut:
    schedules = (
        db.query(models.MedicationSchedule)
        .filter(models.MedicationSchedule.medication_id == med.medication_id)
        .all()
    )
    return schemas.MedicationOut(
        medication_id=med.medication_id,
        medicine_name=med.medicine_name,
        dosage=med.dosage,
        quantity=med.quantity,
        frequency=med.frequency,
        start_date=med.start_date,
        end_date=med.end_date,
        instructions=med.instructions,
        status=med.status,
        schedules=[schemas.MedicationScheduleOut.model_validate(s) for s in schedules],
    )
