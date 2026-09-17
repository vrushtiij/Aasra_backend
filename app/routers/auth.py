from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.deps import get_current_user
from app.firebase import verify_id_token

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()


@router.post("/sync", response_model=schemas.UserOut)
def sync_user(
    body: schemas.AuthSyncRequest,
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
):
    """Call this right after Firebase sign-in on the client. First time it's
    called for a given Firebase account it creates the local `users` row
    (role/name required); every time after that it just returns the existing
    row, so the client can safely call it on every app start."""
    decoded = verify_id_token(creds.credentials)
    if decoded is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")

    firebase_uid = decoded["uid"]
    user = db.query(models.User).filter(models.User.firebase_uid == firebase_uid).first()
    if user:
        return user

    if not body.role or body.role not in ("patient", "caretaker", "doctor"):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "First sync for this account: 'role' is required (patient | caretaker | doctor).",
        )

    # Patients are normally provisioned by a caretaker via POST /patients,
    # which creates the users + patient_profiles rows without a firebase_uid
    # yet. If a matching phone/email already exists (unclaimed), link it
    # instead of creating a duplicate user.
    existing = None
    if decoded.get("phone_number"):
        existing = db.query(models.User).filter(
            models.User.phone == decoded["phone_number"], models.User.firebase_uid.is_(None)
        ).first()
    if existing is None and decoded.get("email"):
        existing = db.query(models.User).filter(
            models.User.email == decoded["email"], models.User.firebase_uid.is_(None)
        ).first()

    if existing:
        existing.firebase_uid = firebase_uid
        db.commit()
        db.refresh(existing)
        return existing

    user = models.User(
        name=body.name or decoded.get("name") or "New User",
        phone=decoded.get("phone_number"),
        email=decoded.get("email"),
        role=body.role,
        language=body.language or "English",
        firebase_uid=firebase_uid,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    if body.role == "patient":
        db.add(models.PatientProfile(patient_id=user.user_id))
        db.commit()

    return user


@router.get("/me", response_model=schemas.UserOut)
def get_me(user: models.User = Depends(get_current_user)):
    return user


@router.put("/me/fcm-token", response_model=schemas.UserOut)
def update_fcm_token(
    body: schemas.FcmTokenUpdate,
    user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register/refresh this device's FCM token so pushes (reminders for the
    patient, alerts for the caregiver) can reach it."""
    user.fcm_token = body.fcm_token
    db.commit()
    db.refresh(user)
    return user
