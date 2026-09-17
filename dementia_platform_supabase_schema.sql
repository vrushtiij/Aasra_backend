-- Dementia Cognitive Assistance Platform
-- Supabase / PostgreSQL schema
-- Run this entire file in Supabase SQL Editor.
-- UUIDs are used for IDs and foreign keys are explicitly connected.

create extension if not exists pgcrypto;

create table public.users (
  user_id uuid primary key default gen_random_uuid(),
  name text not null,
  phone text unique,
  email text unique,
  password_hash text,
  role text not null check (role in ('patient','caretaker','doctor')),
  language text default 'English',
  created_at timestamptz not null default now(),
  status text not null default 'active' check (status in ('active','inactive'))
);

create table public.patient_profiles (
  patient_id uuid primary key references public.users(user_id) on delete cascade,
  date_of_birth date,
  gender text,
  address text,
  emergency_contact text,
  dementia_stage text check (dementia_stage in ('mild','moderate','severe')),
  diagnosis_date date,
  preferred_language text,
  daily_routine text,
  notes text
);

create table public.caretaker_patient (
  relationship_id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patient_profiles(patient_id) on delete cascade,
  caretaker_id uuid not null references public.users(user_id) on delete cascade,
  relationship text,
  is_primary boolean not null default false,
  can_manage_medications boolean not null default true,
  can_view_progress boolean not null default true,
  can_receive_alerts boolean not null default true,
  unique(patient_id, caretaker_id)
);

create table public.medications (
  medication_id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patient_profiles(patient_id) on delete cascade,
  medicine_name text not null,
  dosage text,
  quantity integer,
  frequency text,
  start_date date,
  end_date date,
  instructions text,
  prescribed_by uuid references public.users(user_id) on delete set null,
  status text not null default 'active' check (status in ('active','completed','paused'))
);

create table public.medication_schedule (
  schedule_id uuid primary key default gen_random_uuid(),
  medication_id uuid not null references public.medications(medication_id) on delete cascade,
  time time not null,
  days text default 'daily',
  dose numeric,
  reminder_enabled boolean not null default true,
  grace_period integer default 30
);

create table public.medication_logs (
  log_id uuid primary key default gen_random_uuid(),
  schedule_id uuid not null references public.medication_schedule(schedule_id) on delete cascade,
  patient_id uuid not null references public.patient_profiles(patient_id) on delete cascade,
  scheduled_time timestamptz not null,
  action_time timestamptz,
  status text not null default 'unknown'
    check (status in ('taken','missed','skipped','unknown')),
  confirmed_by uuid references public.users(user_id) on delete set null,
  confirmation_method text check (confirmation_method in ('app','sms','caretaker')),
  reminder_count integer not null default 0,
  alert_sent boolean not null default false
);

create table public.cognitive_games (
  game_id uuid primary key default gen_random_uuid(),
  game_name text not null,
  game_type text not null check (game_type in ('memory','attention','recall','pattern','language','orientation','other')),
  difficulty_level text not null default 'easy'
    check (difficulty_level in ('easy','medium','hard')),
  language text default 'English',
  description text,
  active boolean not null default true
);

create table public.game_sessions (
  session_id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patient_profiles(patient_id) on delete cascade,
  game_id uuid not null references public.cognitive_games(game_id) on delete cascade,
  start_time timestamptz not null default now(),
  end_time timestamptz,
  score numeric,
  accuracy numeric check (accuracy >= 0 and accuracy <= 100),
  difficulty text,
  completion_status text default 'completed'
    check (completion_status in ('completed','abandoned','in_progress'))
);

create table public.cognitive_progress (
  progress_id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patient_profiles(patient_id) on delete cascade,
  date date not null default current_date,
  memory_score numeric,
  attention_score numeric,
  recall_score numeric,
  pattern_score numeric,
  overall_score numeric,
  trend text check (trend in ('improving','stable','declining')),
  unique(patient_id, date)
);

create table public.memory_assistance (
  memory_id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patient_profiles(patient_id) on delete cascade,
  title text not null,
  description text,
  category text check (category in ('person','place','event','task','object','other')),
  date_time timestamptz,
  repeat_type text default 'once',
  created_by uuid references public.users(user_id) on delete set null,
  priority text default 'medium' check (priority in ('low','medium','high')),
  status text default 'active' check (status in ('active','completed','dismissed'))
);

create table public.reminders (
  reminder_id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patient_profiles(patient_id) on delete cascade,
  title text not null,
  description text,
  reminder_type text check (reminder_type in ('meal','appointment','activity','memory','other')),
  date date,
  time time,
  repeat_pattern text default 'once',
  status text default 'pending'
    check (status in ('pending','completed','missed','dismissed')),
  created_by uuid references public.users(user_id) on delete set null
);

create table public.emergency_events (
  event_id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patient_profiles(patient_id) on delete cascade,
  event_type text not null,
  detected_at timestamptz not null default now(),
  severity text default 'medium' check (severity in ('low','medium','high')),
  action_taken text,
  caretaker_notified boolean not null default false,
  resolved boolean not null default false,
  resolved_at timestamptz
);

create table public.offline_sync (
  sync_id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patient_profiles(patient_id) on delete cascade,
  device_id text,
  data_type text not null,
  data_id uuid,
  action text not null check (action in ('create','update','delete')),
  created_at timestamptz not null default now(),
  sync_status text not null default 'pending'
    check (sync_status in ('pending','synced','failed')),
  synced_at timestamptz
);

create table public.sms_alerts (
  sms_id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patient_profiles(patient_id) on delete cascade,
  caretaker_id uuid references public.users(user_id) on delete set null,
  message_type text not null,
  message text not null,
  sent_at timestamptz not null default now(),
  delivery_status text default 'sent'
    check (delivery_status in ('sent','delivered','failed')),
  response text,
  response_time timestamptz
);

create table public.ai_recommendations (
  recommendation_id uuid primary key default gen_random_uuid(),
  patient_id uuid not null references public.patient_profiles(patient_id) on delete cascade,
  recommendation_type text not null
    check (recommendation_type in ('game','reminder','memory','activity','other')),
  recommendation text not null,
  reason text,
  generated_at timestamptz not null default now(),
  accepted boolean,
  feedback text
);

-- Helpful indexes for the most common lookups.
create index idx_medications_patient on public.medications(patient_id);
create index idx_medication_logs_patient on public.medication_logs(patient_id);
create index idx_medication_logs_schedule on public.medication_logs(schedule_id);
create index idx_game_sessions_patient on public.game_sessions(patient_id);
create index idx_cognitive_progress_patient on public.cognitive_progress(patient_id);
create index idx_memory_assistance_patient on public.memory_assistance(patient_id);
create index idx_reminders_patient on public.reminders(patient_id);
create index idx_emergency_events_patient on public.emergency_events(patient_id);
create index idx_offline_sync_patient on public.offline_sync(patient_id);
create index idx_sms_alerts_patient on public.sms_alerts(patient_id);
create index idx_ai_recommendations_patient on public.ai_recommendations(patient_id);

-- Optional trigger: automatically update updated timestamps can be added later
-- if your frontend needs them.
