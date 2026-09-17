from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app import models


# ---------------------------------------------------------
# MVP DEVELOPMENT MODE
# ---------------------------------------------------------
# Authentication is temporarily disabled.
# We use the existing demo caretaker:
# Neha Sharma
# user_id = 00000000-0000-0000-0000-000000000101
#
# DO NOT use this configuration in production.
# ---------------------------------------------------------

MVP_USER_ID = "00000000-0000-0000-0000-000000000101"


def get_current_user(
    db: Session = Depends(get_db),
) -> models.User:
    """Return the fixed demo user for MVP development."""

    user = (
        db.query(models.User)
        .filter(models.User.user_id == MVP_USER_ID)
        .first()
    )

    if user is None:
        raise Exception(
            f"MVP user {MVP_USER_ID} was not found in the database."
        )

    return user


def require_roles(*roles: str):
    """
    MVP mode: authentication/role checks are disabled.

    The endpoint still receives the demo user so existing
    route code does not need to change.
    """

    def _check(user: models.User = Depends(get_current_user)) -> models.User:
        return user

    return _check


require_caretaker = require_roles("caretaker", "doctor")
require_patient = require_roles("patient")


def assert_can_access_patient(patient_id, user: models.User, db: Session):
    """
    MVP mode: patient ownership/link checks are disabled.

    Any patient can be accessed during development.
    """
    return