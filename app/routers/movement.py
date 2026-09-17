from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, assert_can_access_patient
from app.services import summary as summary_service

router = APIRouter(tags=["movement"])


@router.post("/patients/{patient_id}/movement-sessions", response_model=schemas.MovementSessionOut, status_code=status.HTTP_201_CREATED)
def start_movement_session(
    patient_id: str,
    body: schemas.MovementSessionStart,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assert_can_access_patient(patient_id, user, db)
    session = models.MovementSession(
        patient_id=patient_id,
        activity_name=body.activity_name,
        start_time=datetime.now(),
        completion_status="in_progress",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.put("/movement-sessions/{session_id}/finish", response_model=schemas.MovementSessionOut)
def finish_movement_session(
    session_id: str,
    body: schemas.MovementSessionFinish,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(models.MovementSession).filter(models.MovementSession.session_id == session_id).first()
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    assert_can_access_patient(session.patient_id, user, db)

    session.end_time = datetime.now()
    session.accuracy = body.accuracy
    session.completion_status = body.completion_status
    session.notes = body.notes
    db.commit()

    if body.completion_status == "completed":
        summary_service.touch(session.patient_id, db, movement_completed=True)
        db.commit()

    db.refresh(session)
    return session


@router.get("/patients/{patient_id}/movement-sessions", response_model=List[schemas.MovementSessionOut])
def list_movement_sessions(
    patient_id: str,
    limit: int = 20,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assert_can_access_patient(patient_id, user, db)
    rows = (
        db.query(models.MovementSession)
        .filter(models.MovementSession.patient_id == patient_id)
        .order_by(models.MovementSession.start_time.desc())
        .limit(limit)
        .all()
    )
    return rows
