"""
Caregiver alerts, computed on the fly (no alerts table for this MVP) and
delivered via Firebase Cloud Messaging. "Normal" notifications (daily summary
ready) vs. "stronger" alerts (needs attention) are both just FCM pushes; the
strength is conveyed via the notification title/priority on the client.
"""
from datetime import datetime, date
from typing import List, Optional

from sqlalchemy.orm import Session

from app import models
from app.config import settings
from app.firebase import send_push


def get_caretakers_for_patient(patient_id, db: Session, alerts_only: bool = True) -> List[models.User]:
    q = (
        db.query(models.User)
        .join(models.CaretakerPatient, models.CaretakerPatient.caretaker_id == models.User.user_id)
        .filter(models.CaretakerPatient.patient_id == patient_id)
    )
    if alerts_only:
        q = q.filter(models.CaretakerPatient.can_receive_alerts.is_(True))
    return q.all()


def notify_caretakers(
    patient_id,
    title: str,
    body: str,
    db: Session,
    data: Optional[dict] = None,
    alerts_only: bool = True,
) -> int:
    """Pushes to every linked caretaker's registered device. Returns how many
    pushes were actually sent (i.e. had a valid fcm_token)."""
    sent = 0
    for caretaker in get_caretakers_for_patient(patient_id, db, alerts_only=alerts_only):
        if send_push(caretaker.fcm_token, title, body, data=data):
            sent += 1
    return sent


def check_and_alert_missed_medication(log: models.MedicationLog, patient_name: str, db: Session):
    """Call after incrementing reminder_count / marking a medication_log missed.
    Fires a strong alert once the reminder has been repeated past the limit
    and hasn't already been flagged."""
    if log.status == "missed" and not log.alert_sent and log.reminder_count >= settings.REMINDER_REPEAT_LIMIT:
        notify_caretakers(
            log.patient_id,
            title=f"{patient_name} missed a medication",
            body=f"No confirmation after {log.reminder_count} reminders for the scheduled dose.",
            db=db,
            data={"type": "missed_medication", "log_id": str(log.log_id)},
        )
        log.alert_sent = True


def alert_emergency(event: models.EmergencyEvent, patient_name: str, db: Session):
    notify_caretakers(
        event.patient_id,
        title=f"Emergency: {patient_name}",
        body=event.event_type or "Emergency button pressed",
        db=db,
        data={"type": "emergency", "event_id": str(event.event_id)},
    )
    event.caretaker_notified = True


def alert_repeated_uncertainty(patient_id, patient_name: str, db: Session, count: int):
    notify_caretakers(
        patient_id,
        title=f"{patient_name} seems unsure about medication",
        body=f"Marked 'not sure' {count} times recently — a check-in may help.",
        db=db,
        data={"type": "repeated_uncertainty"},
    )


def notify_summary_ready(patient_id, patient_name: str, db: Session):
    notify_caretakers(
        patient_id,
        title="Daily summary ready",
        body=f"{patient_name}'s activity summary for today is ready to view.",
        db=db,
        data={"type": "daily_summary"},
        alerts_only=False,
    )


def compute_open_alerts(patient_id, patient_name: str, db: Session, today: Optional[date] = None) -> list:
    """Read-only version of the same conditions, used by the caregiver
    dashboard's GET /alerts endpoint so nothing needs to be stored."""
    today = today or date.today()
    day_start = datetime.combine(today, datetime.min.time())
    alerts = []

    missed = (
        db.query(models.MedicationLog)
        .filter(
            models.MedicationLog.patient_id == patient_id,
            models.MedicationLog.status == "missed",
            models.MedicationLog.reminder_count >= settings.REMINDER_REPEAT_LIMIT,
            models.MedicationLog.scheduled_time >= day_start,
        )
        .all()
    )
    for log in missed:
        alerts.append({
            "patient_id": patient_id, "patient_name": patient_name,
            "alert_type": "missed_medication", "severity": "high",
            "message": f"Repeated missed medication reminder ({log.reminder_count} reminders sent).",
            "related_id": log.log_id, "triggered_at": log.scheduled_time,
        })

    open_emergencies = (
        db.query(models.EmergencyEvent)
        .filter(models.EmergencyEvent.patient_id == patient_id, models.EmergencyEvent.resolved.is_(False))
        .all()
    )
    for ev in open_emergencies:
        alerts.append({
            "patient_id": patient_id, "patient_name": patient_name,
            "alert_type": "emergency", "severity": "high",
            "message": ev.event_type or "Emergency button pressed",
            "related_id": ev.event_id, "triggered_at": ev.detected_at,
        })

    summary = (
        db.query(models.DailySummary)
        .filter(models.DailySummary.patient_id == patient_id, models.DailySummary.date == today)
        .first()
    )
    now = datetime.now()
    if not summary or not summary.app_used:
        if now.hour >= 11:  # no activity by late morning
            alerts.append({
                "patient_id": patient_id, "patient_name": patient_name,
                "alert_type": "no_app_activity", "severity": "high",
                "message": "No app activity recorded yet today.",
                "related_id": None, "triggered_at": now,
            })
    elif now.hour >= 20 and not (
        summary.cognitive_game_completed and summary.mood_sleep_completed
    ):
        alerts.append({
            "patient_id": patient_id, "patient_name": patient_name,
            "alert_type": "incomplete_daily_activity", "severity": "normal",
            "message": "Today's cognitive activity or mood/sleep check wasn't completed.",
            "related_id": None, "triggered_at": now,
        })

    return alerts
