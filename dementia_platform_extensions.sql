-- Extensions to the Dementia Cognitive Assistance Platform schema
-- Run this AFTER dementia_platform_supabase_schema.sql (and sample data, if used).
-- Kept intentionally small for an MVP: only what's needed to (a) link a user
-- to their Firebase Auth account, (b) send push via FCM, and (c) store the
-- few bits of daily data the spec asks for that don't already have a home.
-- No new tables for notifications/alerts -- those are computed on the fly
-- from existing tables (medication_logs, reminders, emergency_events, etc.)
-- and delivered via Firebase Cloud Messaging, not persisted.

-- Link each app user to their Firebase Auth account, and let us push to
-- their device via FCM.
alter table public.users
  add column if not exists firebase_uid text unique,
  add column if not exists fcm_token text;

-- Memory Lane needs an actual photo and a caregiver-approval flag.
alter table public.memory_assistance
  add column if not exists photo_url text,
  add column if not exists caregiver_approved boolean not null default true;

-- Morning "how did you sleep?" + daily mood check-in.
create table public.mood_sleep_logs (
  log_id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patient_profiles(patient_id) on delete cascade,
  date date not null default current_date,
  sleep_quality text check (sleep_quality in ('good','okay','poor')),
  mood text check (mood in ('happy','okay','sad','anxious','tired')),
  notes text,
  created_at timestamptz not null default now(),
  unique(patient_id, date)
);

-- "Place the phone down, copy the movement shown on screen" activity.
create table public.movement_sessions (
  session_id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patient_profiles(patient_id) on delete cascade,
  activity_name text not null,
  start_time timestamptz not null default now(),
  end_time timestamptz,
  accuracy numeric check (accuracy >= 0 and accuracy <= 100),
  completion_status text not null default 'completed'
    check (completion_status in ('completed','abandoned','in_progress')),
  notes text
);

-- One row per patient per day: the rolled-up numbers the caregiver dashboard
-- and the end-of-day summary push notification are built from.
create table public.daily_summaries (
  summary_id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patient_profiles(patient_id) on delete cascade,
  date date not null default current_date,
  app_used boolean not null default false,
  cognitive_game_completed boolean not null default false,
  mood_sleep_completed boolean not null default false,
  movement_completed boolean not null default false,
  medications_taken integer not null default 0,
  medications_missed integer not null default 0,
  tasks_completed integer not null default 0,
  tasks_total integer not null default 0,
  last_sync timestamptz,
  trend text check (trend in ('improving','stable','declining')),
  generated_at timestamptz not null default now(),
  unique(patient_id, date)
);

create index if not exists idx_mood_sleep_logs_patient on public.mood_sleep_logs(patient_id);
create index if not exists idx_movement_sessions_patient on public.movement_sessions(patient_id);
create index if not exists idx_daily_summaries_patient on public.daily_summaries(patient_id);
