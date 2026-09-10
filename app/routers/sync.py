from datetime import datetime, date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, assert_can_access_patient
from app.services import summary as summary_service
from app.services import alerts as alerts_service

router = APIRouter(tags=["sync"])

SUPPORTED_TYPES = {"medication_log_action", "reminder_status", "mood_sleep_log", "movement_session", "game_session"}


@router.post("/patients/{patient_id}/sync", response_model=schemas.SyncBatchResponse)
def sync_batch(
    patient_id: str,
    body: schemas.SyncBatchRequest,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Everything the patient app recorded locally while offline (medicine
    taken/not taken, tasks done, mood/sleep check, movement/game sessions)
    gets replayed here in order. Each item is logged to offline_sync for
    audit regardless of outcome."""
    assert_can_access_patient(patient_id, user, db)
    now = datetime.now()
    results = []

    for item in body.items:
        sync_row = models.OfflineSync(
            patient_id=patient_id,
            device_id=body.device_id,
            data_type=item.data_type,
            action=item.action,
            created_at=item.created_at or now,
        )
        try:
            if item.data_type not in SUPPORTED_TYPES:
                raise ValueError(f"Unsupported data_type: {item.data_type}")
            _apply_item(patient_id, item, db)
            sync_row.sync_status = "synced"
            sync_row.synced_at = now
            db.add(sync_row)
            db.commit()
            results.append(schemas.SyncBatchResult(data_type=item.data_type, action=item.action, status="synced"))
        except Exception as exc:
            db.rollback()
            sync_row.sync_status = "failed"
            db.add(sync_row)
            db.commit()
            results.append(schemas.SyncBatchResult(data_type=item.data_type, action=item.action, status="failed", detail=str(exc)))

    summary_service.touch(patient_id, db, app_used=True, last_sync=now)
    db.commit()

    return schemas.SyncBatchResponse(synced_at=now, results=results)


def _apply_item(patient_id: str, item: schemas.SyncItem, db: Session):
    payload = item.payload

    if item.data_type == "medication_log_action":
        log = db.query(models.MedicationLog).filter(models.MedicationLog.log_id == payload["log_id"]).first()
        if log is None:
            raise ValueError("medication log not found")
        log.status = payload["status"]
        log.action_time = payload.get("action_time", datetime.now())
        log.confirmation_method = payload.get("confirmation_method", "app")
        db.flush()
        if log.status == "taken":
            summary_service.touch(patient_id, db, medications_taken_delta=1)
        else:
            summary_service.touch(patient_id, db, medications_missed_delta=1)
            patient_user = db.query(models.User).filter(models.User.user_id == patient_id).first()
            alerts_service.check_and_alert_missed_medication(log, patient_user.name, db)

    elif item.data_type == "reminder_status":
        reminder = db.query(models.Reminder).filter(models.Reminder.reminder_id == payload["reminder_id"]).first()
        if reminder is None:
            raise ValueError("reminder not found")
        was_pending = reminder.status == "pending"
        reminder.status = payload["status"]
        db.flush()
        if was_pending:
            summary_service.touch(
                patient_id, db,
                tasks_completed_delta=1 if reminder.status == "completed" else 0,
                tasks_total_delta=1,
            )

    elif item.data_type == "mood_sleep_log":
        log_date = payload.get("date", date.today().isoformat())
        entry = (
            db.query(models.MoodSleepLog)
            .filter(models.MoodSleepLog.patient_id == patient_id, models.MoodSleepLog.date == log_date)
            .first()
        )
        if entry is None:
            entry = models.MoodSleepLog(patient_id=patient_id, date=log_date)
            db.add(entry)
        entry.sleep_quality = payload.get("sleep_quality")
        entry.mood = payload.get("mood")
        entry.notes = payload.get("notes")
        db.flush()
        summary_service.touch(patient_id, db, mood_sleep_completed=True)

    elif item.data_type == "movement_session":
        db.add(models.MovementSession(
            patient_id=patient_id,
            activity_name=payload.get("activity_name", "Movement activity"),
            start_time=payload.get("start_time"),
            end_time=payload.get("end_time", datetime.now()),
            accuracy=payload.get("accuracy"),
            completion_status=payload.get("completion_status", "completed"),
            notes=payload.get("notes"),
        ))
        if payload.get("completion_status", "completed") == "completed":
            summary_service.touch(patient_id, db, movement_completed=True)

    elif item.data_type == "game_session":
        db.add(models.GameSession(
            patient_id=patient_id,
            game_id=payload["game_id"],
            start_time=payload.get("start_time"),
            end_time=payload.get("end_time", datetime.now()),
            score=payload.get("score"),
            accuracy=payload.get("accuracy"),
            difficulty=payload.get("difficulty"),
            completion_status=payload.get("completion_status", "completed"),
        ))
        if payload.get("completion_status", "completed") == "completed":
            summary_service.touch(patient_id, db, cognitive_game_completed=True)

    db.flush()
