# Aasra Backend

FastAPI backend for the Aasra dementia-care app: a patient-facing daily
assistance loop (schedule, reminders, cognitive games, mood/sleep, movement,
Memory Lane, emergency help) and a caregiver dashboard (patient setup,
day-status, alerts, daily summaries).

## 1. Database setup

Run these **in order** against your Postgres/Supabase database:

```
psql $DATABASE_URL -f dementia_platform_supabase_schema.sql
psql $DATABASE_URL -f dementia_platform_sample_data.sql      # optional demo data
psql $DATABASE_URL -f dementia_platform_extensions.sql       # required — adds
                                                               # firebase_uid/fcm_token
                                                               # to users, photo fields
                                                               # to memory_assistance, and
                                                               # 3 small new tables
```

`dementia_platform_extensions.sql` is intentionally minimal for this MVP:
it does **not** add notification/alert tables — those are computed on the fly
and delivered via Firebase Cloud Messaging instead of being stored.

## 2. Firebase setup

Auth is handled entirely by **Firebase Auth** on the client (mobile app /
caregiver dashboard sign in directly with Firebase — email, phone, whatever
you configure). This backend never issues or stores passwords; it only:

- verifies the Firebase ID token sent as `Authorization: Bearer <token>`
- links that Firebase account to a row in `public.users` via `firebase_uid`
- sends push notifications via **Firebase Cloud Messaging (FCM)**

Create a Firebase project, enable the sign-in methods you want, and generate
a service-account key (Project Settings → Service Accounts → Generate new
private key). Point the backend at it via one of:

```
FIREBASE_CREDENTIALS_PATH=./serviceAccountKey.json
# or
FIREBASE_CREDENTIALS_JSON={"type": "service_account", ...}
```

## 3. Environment

Copy `.env.example` to `.env` and fill in `DATABASE_URL` and the Firebase
credentials above.

## 4. Run

```
pip install -r requirements.txt
uvicorn main:app --reload
```

Docs at `http://localhost:8000/docs`.

## How auth works end-to-end

1. Client signs in with Firebase Auth SDK directly → gets an ID token.
2. Client calls `POST /auth/sync` with that token (and `role` the first
   time). This creates/links the local `users` row.
   - For **patients**, the row is normally created ahead of time by a
     caregiver via `POST /patients` (no `firebase_uid` yet). When the
     patient's device later calls `/auth/sync`, it's auto-linked by matching
     phone/email.
   - For **caregivers/doctors**, `/auth/sync` creates the row on first call.
3. Every other endpoint takes the same Bearer token; `GET /auth/me` returns
   the linked user.
4. Client calls `PUT /auth/me/fcm-token` to register its device for push.

## How alerts/notifications work

There's no `notifications`/`alerts` table. Instead:

- **Patient-facing reminders** (medicine, meals, appointments, tasks) live in
  `medication_logs` / `reminders`. The patient app fetches what's due
  (`GET /patients/{id}/medication-logs/today`, `.../reminders/today`) and
  shows its own large, voice-read, repeating local notification with
  Taken/Not Taken or Done/Not Yet buttons; it calls back into the API
  (`POST /medication-logs/{id}/action`, `.../repeat`, `PUT /reminders/{id}/status`)
  to record the result. This is what keeps things working offline.
- **Caregiver alerts** ("stronger" pushes: missed medication streak, no
  activity, repeated uncertainty, incomplete day, emergency) are computed
  from existing tables on request (`GET /patients/{id}/alerts`) and pushed
  proactively via FCM the moment the underlying condition is detected (see
  `app/services/alerts.py`), straight to each linked caregiver's registered
  device.
- **Normal notifications** ("your daily summary is ready") are also just an
  FCM push (`POST /patients/{id}/generate-summary`), sent to *all* linked
  caregivers rather than only ones with `can_receive_alerts` enabled.

## Project layout

```
main.py                 entry point (uvicorn main:app)
app/
  main.py                FastAPI app + router registration
  config.py               env/settings
  database.py              SQLAlchemy engine/session
  models.py                 ORM models mapped to the existing schema
  schemas.py                Pydantic request/response models
  deps.py                    Firebase-token auth + role/ownership checks
  firebase.py                Firebase Admin init, token verify, FCM push
  routers/
    auth.py         sync/me/fcm-token
    patients.py      caregiver setup + patient list/profile
    medications.py    medication + schedule CRUD, Taken/Not Taken logging
    reminders.py       meal/appointment/task reminders, Done/Not Yet
    games.py             cognitive games, adaptive session start/finish, progress
    mood.py                mood/sleep check-in
    movement.py             movement (copy-the-motion) activity
    memory_lane.py           caregiver-approved photos/prompts
    emergency.py               emergency button + resolution
    sync.py                      offline batch sync from the patient app
    dashboard.py                  day-status, alerts, summary generation
    home.py                        patient's "first open today" screen
  services/
    alerts.py         alert condition checks + FCM push helpers
    summary.py          daily_summaries upsert helper used across routers
```
