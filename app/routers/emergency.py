from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, require_caretaker, assert_can_access_patient
from app.services import alerts as alerts_service

router = APIRouter(tags=["emergency"])


@router.post("/patients/{patient_id}/emergency", response_model=schemas.EmergencyEventOut, status_code=status.HTTP_201_CREATED)
def trigger_emergency(
    patient_id: str,
    body: schemas.EmergencyTrigger,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The permanent emergency-help button. Fires an immediate high-priority
    FCM push to every linked caretaker, regardless of their alert preference."""
    assert_can_access_patient(patient_id, user, db)
    event = models.EmergencyEvent(
        patient_id=patient_id,
        event_type=body.event_type or "Emergency button pressed",
        detected_at=datetime.now(),
        severity="high",
        action_taken=body.notes,
    )
    db.add(event)
    db.flush()

    patient_user = db.query(models.User).filter(models.User.user_id == patient_id).first()
    alerts_service.alert_emergency(event, patient_user.name, db)

    db.commit()
    db.refresh(event)
    return event


@router.get("/patients/{patient_id}/emergency", response_model=List[schemas.EmergencyEventOut])
def list_emergency_events(
    patient_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assert_can_access_patient(patient_id, user, db)
    rows = (
        db.query(models.EmergencyEvent)
        .filter(models.EmergencyEvent.patient_id == patient_id)
        .order_by(models.EmergencyEvent.detected_at.desc())
        .all()
    )
    return rows


@router.put("/emergency/{event_id}/resolve", response_model=schemas.EmergencyEventOut)
def resolve_emergency(
    event_id: str,
    body: schemas.EmergencyResolve,
    caretaker: models.User = Depends(require_caretaker),
    db: Session = Depends(get_db),
):
    event = db.query(models.EmergencyEvent).filter(models.EmergencyEvent.event_id == event_id).first()
    if event is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")
    assert_can_access_patient(event.patient_id, caretaker, db)

    event.resolved = True
    event.resolved_at = datetime.now()
    if body.action_taken:
        event.action_taken = body.action_taken
    db.commit()
    db.refresh(event)
    return event
