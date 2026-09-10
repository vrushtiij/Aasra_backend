import uuid
from sqlalchemy import (
    Column, Text, Boolean, Integer, Numeric, Date, Time, DateTime, ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


def uuid_col(primary_key=False, fk=None, nullable=True):
    if fk:
        return Column(UUID(as_uuid=True), ForeignKey(fk), primary_key=primary_key, nullable=nullable)
    return Column(UUID(as_uuid=True), primary_key=primary_key, default=uuid.uuid4)


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}

    user_id = uuid_col(primary_key=True)
    name = Column(Text, nullable=False)
    phone = Column(Text, unique=True)
    email = Column(Text, unique=True)
    password_hash = Column(Text)  # unused now that auth is via Firebase; kept for schema compatibility
    role = Column(Text, nullable=False)  # patient | caretaker | doctor
    language = Column(Text, default="English")
    created_at = Column(DateTime(timezone=True))
    status = Column(Text, nullable=False, default="active")
    firebase_uid = Column(Text, unique=True)
    fcm_token = Column(Text)


class PatientProfile(Base):
    __tablename__ = "patient_profiles"
    __table_args__ = {"schema": "public"}

    patient_id = uuid_col(primary_key=True, fk="public.users.user_id")
    date_of_birth = Column(Date)
    gender = Column(Text)
    address = Column(Text)
    emergency_contact = Column(Text)
    dementia_stage = Column(Text)
    diagnosis_date = Column(Date)
    preferred_language = Column(Text)
    daily_routine = Column(Text)
    notes = Column(Text)


class CaretakerPatient(Base):
    __tablename__ = "caretaker_patient"
    __table_args__ = {"schema": "public"}

    relationship_id = uuid_col(primary_key=True)
    patient_id = uuid_col(fk="public.patient_profiles.patient_id", nullable=False)
    caretaker_id = uuid_col(fk="public.users.user_id", nullable=False)
    relationship_label = Column("relationship", Text)
    is_primary = Column(Boolean, nullable=False, default=False)
    can_manage_medications = Column(Boolean, nullable=False, default=True)
    can_view_progress = Column(Boolean, nullable=False, default=True)
    can_receive_alerts = Column(Boolean, nullable=False, default=True)


class Medication(Base):
    __tablename__ = "medications"
    __table_args__ = {"schema": "public"}

    medication_id = uuid_col(primary_key=True)
    patient_id = uuid_col(fk="public.patient_profiles.patient_id", nullable=False)
    medicine_name = Column(Text, nullable=False)
    dosage = Column(Text)
    quantity = Column(Integer)
    frequency = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    instructions = Column(Text)
    prescribed_by = uuid_col(fk="public.users.user_id")
    status = Column(Text, nullable=False, default="active")


class MedicationSchedule(Base):
    __tablename__ = "medication_schedule"
    __table_args__ = {"schema": "public"}

    schedule_id = uuid_col(primary_key=True)
    medication_id = uuid_col(fk="public.medications.medication_id", nullable=False)
    time = Column(Time, nullable=False)
    days = Column(Text, default="daily")
    dose = Column(Numeric)
    reminder_enabled = Column(Boolean, nullable=False, default=True)
    grace_period = Column(Integer, default=30)


class MedicationLog(Base):
    __tablename__ = "medication_logs"
    __table_args__ = {"schema": "public"}

    log_id = uuid_col(primary_key=True)
    schedule_id = uuid_col(fk="public.medication_schedule.schedule_id", nullable=False)
    patient_id = uuid_col(fk="public.patient_profiles.patient_id", nullable=False)
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    action_time = Column(DateTime(timezone=True))
    status = Column(Text, nullable=False, default="unknown")
    confirmed_by = uuid_col(fk="public.users.user_id")
    confirmation_method = Column(Text)
    reminder_count = Column(Integer, nullable=False, default=0)
    alert_sent = Column(Boolean, nullable=False, default=False)


class CognitiveGame(Base):
    __tablename__ = "cognitive_games"
    __table_args__ = {"schema": "public"}

    game_id = uuid_col(primary_key=True)
    game_name = Column(Text, nullable=False)
    game_type = Column(Text, nullable=False)
    difficulty_level = Column(Text, nullable=False, default="easy")
    language = Column(Text, default="English")
    description = Column(Text)
    active = Column(Boolean, nullable=False, default=True)


class GameSession(Base):
    __tablename__ = "game_sessions"
    __table_args__ = {"schema": "public"}

    session_id = uuid_col(primary_key=True)
    patient_id = uuid_col(fk="public.patient_profiles.patient_id", nullable=False)
    game_id = uuid_col(fk="public.cognitive_games.game_id", nullable=False)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    score = Column(Numeric)
    accuracy = Column(Numeric)
    difficulty = Column(Text)
    completion_status = Column(Text, default="completed")


class CognitiveProgress(Base):
    __tablename__ = "cognitive_progress"
    __table_args__ = {"schema": "public"}

    progress_id = uuid_col(primary_key=True)
    patient_id = uuid_col(fk="public.patient_profiles.patient_id", nullable=False)
    date = Column(Date, nullable=False)
    memory_score = Column(Numeric)
    attention_score = Column(Numeric)
    recall_score = Column(Numeric)
    pattern_score = Column(Numeric)
    overall_score = Column(Numeric)
    trend = Column(Text)


class MemoryAssistance(Base):
    __tablename__ = "memory_assistance"
    __table_args__ = {"schema": "public"}

    memory_id = uuid_col(primary_key=True)
    patient_id = uuid_col(fk="public.patient_profiles.patient_id", nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text)
    category = Column(Text)
    date_time = Column(DateTime(timezone=True))
    repeat_type = Column(Text, default="once")
    created_by = uuid_col(fk="public.users.user_id")
    priority = Column(Text, default="medium")
    status = Column(Text, default="active")
    photo_url = Column(Text)
    caregiver_approved = Column(Boolean, nullable=False, default=True)


class Reminder(Base):
    __tablename__ = "reminders"
    __table_args__ = {"schema": "public"}

    reminder_id = uuid_col(primary_key=True)
    patient_id = uuid_col(fk="public.patient_profiles.patient_id", nullable=False)
    title = Column(Text, nullable=False)
    description = Column(Text)
    reminder_type = Column(Text)
    date = Column(Date)
    time = Column(Time)
    repeat_pattern = Column(Text, default="once")
    status = Column(Text, default="pending")
    created_by = uuid_col(fk="public.users.user_id")


class EmergencyEvent(Base):
    __tablename__ = "emergency_events"
    __table_args__ = {"schema": "public"}

    event_id = uuid_col(primary_key=True)
    patient_id = uuid_col(fk="public.patient_profiles.patient_id", nullable=False)
    event_type = Column(Text, nullable=False)
    detected_at = Column(DateTime(timezone=True))
    severity = Column(Text, default="medium")
    action_taken = Column(Text)
    caretaker_notified = Column(Boolean, nullable=False, default=False)
    resolved = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime(timezone=True))


class OfflineSync(Base):
    __tablename__ = "offline_sync"
    __table_args__ = {"schema": "public"}

    sync_id = uuid_col(primary_key=True)
    patient_id = uuid_col(fk="public.patient_profiles.patient_id", nullable=False)
    device_id = Column(Text)
    data_type = Column(Text, nullable=False)
    data_id = Column(UUID(as_uuid=True))
    action = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True))
    sync_status = Column(Text, nullable=False, default="pending")
    synced_at = Column(DateTime(timezone=True))


class SmsAlert(Base):
    __tablename__ = "sms_alerts"
    __table_args__ = {"schema": "public"}

    sms_id = uuid_col(primary_key=True)
    patient_id = uuid_col(fk="public.patient_profiles.patient_id", nullable=False)
    caretaker_id = uuid_col(fk="public.users.user_id")
    message_type = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True))
    delivery_status = Column(Text, default="sent")
    response = Column(Text)
    response_time = Column(DateTime(timezone=True))


class AiRecommendation(Base):
    __tablename__ = "ai_recommendations"
    __table_args__ = {"schema": "public"}

    recommendation_id = uuid_col(primary_key=True)
    patient_id = uuid_col(fk="public.patient_profiles.patient_id", nullable=False)
    recommendation_type = Column(Text, nullable=False)
    recommendation = Column(Text, nullable=False)
    reason = Column(Text)
    generated_at = Column(DateTime(timezone=True))
    accepted = Column(Boolean)
    feedback = Column(Text)


# -- New (MVP-minimal) tables from dementia_platform_extensions.sql --------

class MoodSleepLog(Base):
    __tablename__ = "mood_sleep_logs"
    __table_args__ = {"schema": "public"}

    log_id = uuid_col(primary_key=True)
    patient_id = uuid_col(fk="public.patient_profiles.patient_id", nullable=False)
    date = Column(Date, nullable=False)
    sleep_quality = Column(Text)
    mood = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True))


class MovementSession(Base):
    __tablename__ = "movement_sessions"
    __table_args__ = {"schema": "public"}

    session_id = uuid_col(primary_key=True)
    patient_id = uuid_col(fk="public.patient_profiles.patient_id", nullable=False)
    activity_name = Column(Text, nullable=False)
    start_time = Column(DateTime(timezone=True))
    end_time = Column(DateTime(timezone=True))
    accuracy = Column(Numeric)
    completion_status = Column(Text, default="completed")
    notes = Column(Text)


class DailySummary(Base):
    __tablename__ = "daily_summaries"
    __table_args__ = {"schema": "public"}

    summary_id = uuid_col(primary_key=True)
    patient_id = uuid_col(fk="public.patient_profiles.patient_id", nullable=False)
    date = Column(Date, nullable=False)
    app_used = Column(Boolean, nullable=False, default=False)
    cognitive_game_completed = Column(Boolean, nullable=False, default=False)
    mood_sleep_completed = Column(Boolean, nullable=False, default=False)
    movement_completed = Column(Boolean, nullable=False, default=False)
    medications_taken = Column(Integer, nullable=False, default=0)
    medications_missed = Column(Integer, nullable=False, default=0)
    tasks_completed = Column(Integer, nullable=False, default=0)
    tasks_total = Column(Integer, nullable=False, default=0)
    last_sync = Column(DateTime(timezone=True))
    trend = Column(Text)
    generated_at = Column(DateTime(timezone=True))
