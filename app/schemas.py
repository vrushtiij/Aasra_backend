import uuid
import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- auth ----

class AuthSyncRequest(BaseModel):
    role: Optional[str] = Field(
        None,
        description="Required only the first time this Firebase user logs in: patient | caretaker | doctor"
    )
    name: Optional[str] = None
    language: Optional[str] = "English"


class UserOut(ORMModel):
    user_id: uuid.UUID
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    role: str
    language: Optional[str] = None
    status: str


class FcmTokenUpdate(BaseModel):
    fcm_token: str


# ------------------------------------------------------- patient setup ----

class PatientCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    language: Optional[str] = "English"
    date_of_birth: Optional[datetime.date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    dementia_stage: Optional[str] = None
    diagnosis_date: Optional[datetime.date] = None
    preferred_language: Optional[str] = None
    daily_routine: Optional[str] = None
    notes: Optional[str] = None
    relationship: Optional[str] = Field(
        None,
        description="e.g. Daughter, Son, Nurse"
    )


class PatientProfileUpdate(BaseModel):
    name: Optional[str] = None
    date_of_birth: Optional[datetime.date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    dementia_stage: Optional[str] = None
    diagnosis_date: Optional[datetime.date] = None
    preferred_language: Optional[str] = None
    daily_routine: Optional[str] = None
    notes: Optional[str] = None


class PatientOut(ORMModel):
    patient_id: uuid.UUID
    name: str
    language: Optional[str] = None
    date_of_birth: Optional[datetime.date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    emergency_contact: Optional[str] = None
    dementia_stage: Optional[str] = None
    diagnosis_date: Optional[datetime.date] = None
    preferred_language: Optional[str] = None
    daily_routine: Optional[str] = None
    notes: Optional[str] = None


class PatientListItem(BaseModel):
    patient_id: uuid.UUID
    name: str
    dementia_stage: Optional[str] = None
    used_app_today: bool
    last_sync: Optional[datetime.datetime] = None
    relationship: Optional[str] = None
    is_primary: bool


# -------------------------------------------------------- medications -----

class MedicationCreate(BaseModel):
    medicine_name: str
    dosage: Optional[str] = None
    quantity: Optional[int] = None
    frequency: Optional[str] = None
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    instructions: Optional[str] = None
    times: List[datetime.time] = Field(
        default_factory=list,
        description="One schedule row is created per time of day"
    )
    days: Optional[str] = "daily"
    grace_period: Optional[int] = 30


class MedicationScheduleOut(ORMModel):
    schedule_id: uuid.UUID
    time: datetime.time
    days: Optional[str] = None
    reminder_enabled: bool
    grace_period: Optional[int] = None


class MedicationOut(ORMModel):
    medication_id: uuid.UUID
    medicine_name: str
    dosage: Optional[str] = None
    quantity: Optional[int] = None
    frequency: Optional[str] = None
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    instructions: Optional[str] = None
    status: str
    schedules: List[MedicationScheduleOut] = Field(default_factory=list)


class MedicationLogActionRequest(BaseModel):
    status: str = Field(..., description="taken | missed | skipped")
    confirmation_method: Optional[str] = Field(
        "app",
        description="app | sms | caretaker"
    )


class MedicationLogOut(ORMModel):
    log_id: uuid.UUID
    schedule_id: uuid.UUID
    scheduled_time: datetime.datetime
    action_time: Optional[datetime.datetime] = None
    status: str
    reminder_count: int


# ------------------------------------------------------------ reminders ---

class ReminderCreate(BaseModel):
    title: str
    description: Optional[str] = None
    reminder_type: Optional[str] = Field(
        None,
        description="meal | appointment | activity | memory | other"
    )
    date: Optional[datetime.date] = None
    time: Optional[datetime.time] = None
    repeat_pattern: Optional[str] = "once"


class ReminderOut(ORMModel):
    reminder_id: uuid.UUID
    title: str
    description: Optional[str] = None
    reminder_type: Optional[str] = None
    date: Optional[datetime.date] = None
    time: Optional[datetime.time] = None
    repeat_pattern: Optional[str] = None
    status: str


class ReminderStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        description="completed | missed | dismissed"
    )


# ---------------------------------------------------------------- games ---

class CognitiveGameOut(ORMModel):
    game_id: uuid.UUID
    game_name: str
    game_type: str
    difficulty_level: str
    language: Optional[str] = None
    description: Optional[str] = None


class GameSessionStart(BaseModel):
    game_id: Optional[uuid.UUID] = Field(
        None,
        description="Omit to let the backend pick the next adaptive game"
    )
    difficulty: Optional[str] = None


class GameSessionFinish(BaseModel):
    score: Optional[float] = None
    accuracy: float = Field(..., ge=0, le=100)
    completion_status: str = Field(
        "completed",
        description="completed | abandoned"
    )


class GameSessionOut(ORMModel):
    session_id: uuid.UUID
    game_id: uuid.UUID
    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    score: Optional[float] = None
    accuracy: Optional[float] = None
    difficulty: Optional[str] = None
    completion_status: Optional[str] = None


class CognitiveProgressOut(ORMModel):
    date: datetime.date
    memory_score: Optional[float] = None
    attention_score: Optional[float] = None
    recall_score: Optional[float] = None
    pattern_score: Optional[float] = None
    overall_score: Optional[float] = None
    trend: Optional[str] = None


# ------------------------------------------------------------ mood/sleep --

class MoodSleepCreate(BaseModel):
    sleep_quality: Optional[str] = Field(
        None,
        description="good | okay | poor"
    )
    mood: Optional[str] = Field(
        None,
        description="happy | okay | sad | anxious | tired"
    )
    notes: Optional[str] = None


class MoodSleepOut(ORMModel):
    log_id: uuid.UUID
    date: datetime.date
    sleep_quality: Optional[str] = None
    mood: Optional[str] = None
    notes: Optional[str] = None


# ------------------------------------------------------------- movement ---

class MovementSessionStart(BaseModel):
    activity_name: str


class MovementSessionFinish(BaseModel):
    accuracy: Optional[float] = Field(None, ge=0, le=100)
    completion_status: str = Field(
        "completed",
        description="completed | abandoned"
    )
    notes: Optional[str] = None


class MovementSessionOut(ORMModel):
    session_id: uuid.UUID
    activity_name: str
    start_time: Optional[datetime.datetime] = None
    end_time: Optional[datetime.datetime] = None
    accuracy: Optional[float] = None
    completion_status: str


# ---------------------------------------------------------- memory lane ---

class MemoryItemCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: Optional[str] = Field(
        None,
        description="person | place | event | task | object | other"
    )
    date_time: Optional[datetime.datetime] = None
    repeat_type: Optional[str] = "once"
    priority: Optional[str] = "medium"
    photo_url: Optional[str] = None
    caregiver_approved: Optional[bool] = True


class MemoryItemOut(ORMModel):
    memory_id: uuid.UUID
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    date_time: Optional[datetime.datetime] = None
    repeat_type: Optional[str] = None
    priority: Optional[str] = None
    status: str
    photo_url: Optional[str] = None
    caregiver_approved: bool


# ------------------------------------------------------------- emergency --

class EmergencyTrigger(BaseModel):
    event_type: Optional[str] = "Emergency button pressed"
    notes: Optional[str] = None


class EmergencyEventOut(ORMModel):
    event_id: uuid.UUID
    event_type: str
    detected_at: Optional[datetime.datetime] = None
    severity: Optional[str] = None
    action_taken: Optional[str] = None
    caretaker_notified: bool
    resolved: bool
    resolved_at: Optional[datetime.datetime] = None


class EmergencyResolve(BaseModel):
    action_taken: Optional[str] = None


# --------------------------------------------------------- offline sync ---

class SyncItem(BaseModel):
    data_type: str = Field(
        ...,
        description="e.g. medication_log, reminder, game_session, mood_sleep_log, movement_session"
    )
    action: str = Field(
        ...,
        description="create | update | delete"
    )
    device_id: Optional[str] = None
    payload: dict = Field(
        default_factory=dict,
        description="The fields for the underlying record"
    )
    created_at: Optional[datetime.datetime] = None


class SyncBatchRequest(BaseModel):
    device_id: str
    items: List[SyncItem]


class SyncBatchResult(BaseModel):
    data_type: str
    action: str
    status: str
    detail: Optional[str] = None


class SyncBatchResponse(BaseModel):
    synced_at: datetime.datetime
    results: List[SyncBatchResult]


# ------------------------------------------------------------- dashboard --

class PatientDayStatus(BaseModel):
    patient_id: uuid.UUID
    date: datetime.date
    app_used: bool
    cognitive_game_completed: bool
    mood_sleep_completed: bool
    movement_completed: bool
    medications_taken: int
    medications_missed: int
    medications_total: int
    tasks_completed: int
    tasks_total: int
    last_sync: Optional[datetime.datetime] = None
    trend: Optional[str] = None


class AlertOut(BaseModel):
    patient_id: uuid.UUID
    patient_name: str
    alert_type: str
    severity: str = "high"
    message: str
    related_id: Optional[uuid.UUID] = None
    triggered_at: datetime.datetime