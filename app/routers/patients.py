from datetime import date, datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user, require_caretaker, assert_can_access_patient

router = APIRouter(prefix="/patients", tags=["patients"])


@router.post("", response_model=schemas.PatientOut, status_code=status.HTTP_201_CREATED)
def create_patient(
    body: schemas.PatientCreate,
    caretaker: models.User = Depends(require_caretaker),
    db: Session = Depends(get_db),
):
    """Caregiver setup step 1: create the patient profile. The patient row is
    created without a firebase_uid; it gets linked automatically the first
    time that patient signs in with a matching phone/email via POST /auth/sync."""
    user = models.User(
        name=body.name,
        phone=body.phone,
        email=body.email,
        role="patient",
        language=body.language or "English",
        created_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.flush()

    profile = models.PatientProfile(
        patient_id=user.user_id,
        date_of_birth=body.date_of_birth,
        gender=body.gender,
        address=body.address,
        emergency_contact=body.emergency_contact,
        dementia_stage=(
    "mild"
    if body.dementia_stage == "Mild Cognitive Impairment"
    else body.dementia_stage.lower() if body.dementia_stage else None
),
        diagnosis_date=body.diagnosis_date,
        preferred_language=body.preferred_language or body.language,
        daily_routine=body.daily_routine,
        notes=body.notes,
    )
    db.add(profile)
    db.flush()
    link = models.CaretakerPatient(
        patient_id=user.user_id,
        caretaker_id=caretaker.user_id,
        relationship_label=body.relationship,
        is_primary=True,
    )
    db.add(link)
    db.commit()
    db.refresh(profile)
    return _to_patient_out(profile, user.name)


@router.get("", response_model=List[schemas.PatientListItem])
def list_patients(
    caretaker: models.User = Depends(require_caretaker),
    db: Session = Depends(get_db),
):
    """Caregiver dashboard: all patients linked to this caretaker, with
    today's at-a-glance status."""
    links = (
        db.query(models.CaretakerPatient)
        .filter(models.CaretakerPatient.caretaker_id == caretaker.user_id)
        .all()
    )
    today = date.today()
    out = []
    for link in links:
        user = db.query(models.User).filter(models.User.user_id == link.patient_id).first()
        profile = db.query(models.PatientProfile).filter(models.PatientProfile.patient_id == link.patient_id).first()
        summary = (
            db.query(models.DailySummary)
            .filter(models.DailySummary.patient_id == link.patient_id, models.DailySummary.date == today)
            .first()
        )
        out.append(schemas.PatientListItem(
            patient_id=link.patient_id,
            name=user.name if user else "Unknown",
            dementia_stage=profile.dementia_stage if profile else None,
            used_app_today=bool(summary.app_used) if summary else False,
            last_sync=summary.last_sync if summary else None,
            relationship=link.relationship_label,
            is_primary=link.is_primary,
        ))
    return out


@router.get("/{patient_id}", response_model=schemas.PatientOut)
def get_patient(
    patient_id: str,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assert_can_access_patient(patient_id, user, db)
    profile = db.query(models.PatientProfile).filter(models.PatientProfile.patient_id == patient_id).first()
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    patient_user = db.query(models.User).filter(models.User.user_id == patient_id).first()
    return _to_patient_out(profile, patient_user.name)


@router.put("/{patient_id}", response_model=schemas.PatientOut)
def update_patient(
    patient_id: str,
    body: schemas.PatientProfileUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    assert_can_access_patient(patient_id, user, db)
    profile = db.query(models.PatientProfile).filter(models.PatientProfile.patient_id == patient_id).first()
    if profile is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    patient_user = db.query(models.User).filter(models.User.user_id == patient_id).first()

    data = body.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        patient_user.name = data.pop("name")
    for field, value in data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return _to_patient_out(profile, patient_user.name)


def _to_patient_out(profile: models.PatientProfile, name: str) -> schemas.PatientOut:
    return schemas.PatientOut(
        patient_id=profile.patient_id,
        name=name,
        date_of_birth=profile.date_of_birth,
        gender=profile.gender,
        address=profile.address,
        emergency_contact=profile.emergency_contact,
        dementia_stage=profile.dementia_stage,
        diagnosis_date=profile.diagnosis_date,
        preferred_language=profile.preferred_language,
        daily_routine=profile.daily_routine,
        notes=profile.notes,
    )
