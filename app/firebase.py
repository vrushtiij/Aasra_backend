"""
Firebase integration for the Aasra backend.

- Auth: the mobile/dashboard apps sign in with Firebase Auth directly (email,
  phone, etc). They send the resulting Firebase ID token to us as a Bearer
  token; we only ever verify it here, we never issue or store our own
  passwords/tokens.
- Push: caregiver alerts and patient reminders are delivered via Firebase
  Cloud Messaging (FCM) to whatever device token the app registered.

Requires a Firebase service-account key, set via one of:
  FIREBASE_CREDENTIALS_PATH=/path/to/serviceAccount.json
  FIREBASE_CREDENTIALS_JSON='{"type": "service_account", ...}'
"""
import json
import logging
from typing import Optional

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth, messaging

from app.config import settings

logger = logging.getLogger("aasra.firebase")

_firebase_app = None


def init_firebase():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    if settings.FIREBASE_CREDENTIALS_JSON:
        cred = credentials.Certificate(json.loads(settings.FIREBASE_CREDENTIALS_JSON))
    elif settings.FIREBASE_CREDENTIALS_PATH:
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
    else:
        logger.warning(
            "No Firebase credentials configured (FIREBASE_CREDENTIALS_PATH / "
            "FIREBASE_CREDENTIALS_JSON). Auth and push notifications will fail "
            "until this is set."
        )
        return None

    _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


def verify_id_token(id_token: str) -> Optional[dict]:
    """Verify a Firebase ID token. Returns the decoded token dict, or None."""
    try:
        return firebase_auth.verify_id_token(id_token)
    except Exception as exc:  # invalid, expired, revoked, etc.
        logger.info("Firebase token verification failed: %s", exc)
        return None


def send_push(fcm_token: Optional[str], title: str, body: str, data: Optional[dict] = None) -> bool:
    """Send a push notification via FCM. Silently no-ops if there's no token
    or Firebase isn't configured, so the rest of the request never fails
    because of a missing/expired device token."""
    if not fcm_token:
        return False
    if _firebase_app is None and init_firebase() is None:
        return False
    try:
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=fcm_token,
        )
        messaging.send(message)
        return True
    except Exception as exc:
        logger.warning("FCM push failed: %s", exc)
        return False
