from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, require_caretaker, assert_can_access_patient

router = APIRouter(tags=["memory-lane"])


@router.post("/patients/{patient_id}/memory-lane", response_model=schemas.MemoryItemOut, status_code=status.HTTP_201_CREATED)
def create_memory_item(
    patient_id: str,
    body: schemas.MemoryItemCreate,
    caretaker: models.User = Depends(require_caretaker),
    db: Session = Depends(get_db),
):
    """Caregivers add family/place photos and memory prompts. Items are
    caregiver_approved by default since only caregivers can create them here;
    the flag exists so a caregiver can stage something and unapprove it later
    without deleting it."""
    assert_can_access_patient(patient_id, caretaker, db)
    item = models.MemoryAssistance(
        patient_id=patient_id,
        title=body.title,
        description=body.description,
        category=body.category,
        date_time=body.date_time,
        repeat_type=body.repeat_type or "once",
        created_by=caretaker.user_id,
        priority=body.priority or "medium",
        photo_url=body.photo_url,
        caregiver_approved=body.caregiver_approved if body.caregiver_approved is not None else True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/patients/{patient_id}/memory-lane", response_model=List[schemas.MemoryItemOut])
def list_memory_items(
    patient_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """The patient app should only ever render caregiver_approved items."""
    assert_can_access_patient(patient_id, user, db)
    q = db.query(models.MemoryAssistance).filter(models.MemoryAssistance.patient_id == patient_id)
    if user.role == "patient":
        q = q.filter(models.MemoryAssistance.caregiver_approved.is_(True), models.MemoryAssistance.status == "active")
    return q.order_by(models.MemoryAssistance.priority.desc()).all()


@router.put("/memory-lane/{memory_id}", response_model=schemas.MemoryItemOut)
def update_memory_item(
    memory_id: str,
    body: schemas.MemoryItemCreate,
    caretaker: models.User = Depends(require_caretaker),
    db: Session = Depends(get_db),
):
    item = db.query(models.MemoryAssistance).filter(models.MemoryAssistance.memory_id == memory_id).first()
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Memory item not found")
    assert_can_access_patient(item.patient_id, caretaker, db)

    for field in ("title", "description", "category", "date_time", "repeat_type", "priority", "photo_url"):
        setattr(item, field, getattr(body, field))
    if body.caregiver_approved is not None:
        item.caregiver_approved = body.caregiver_approved
    db.commit()
    db.refresh(item)
    return item


@router.delete("/memory-lane/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_memory_item(
    memory_id: str,
    caretaker: models.User = Depends(require_caretaker),
    db: Session = Depends(get_db),
):
    item = db.query(models.MemoryAssistance).filter(models.MemoryAssistance.memory_id == memory_id).first()
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Memory item not found")
    assert_can_access_patient(item.patient_id, caretaker, db)
    item.status = "dismissed"
    db.commit()
