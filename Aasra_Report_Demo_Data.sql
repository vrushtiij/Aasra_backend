-- AASRA DEMO / REPORT TEST DATA
-- Uses ONLY tables and cognitive games that already exist in your Aasra project.
-- Does NOT create games, new features, or new tables.
-- Run this AFTER your existing Aasra schema/extension SQL and after at least
-- one patient already exists in public.users.
--
-- It adds 90 days of TEST data to the first existing patient so you can test:
-- 7 / 30 / 60 / 90 day reports
-- Daily / Weekly / Monthly graph views
--
-- IMPORTANT: This is demo data, not real patient data.

DO $$
DECLARE
  p_id uuid;
  g_ids uuid[];
BEGIN
  -- Use an existing patient. No patient is created.
  SELECT u.user_id
  INTO p_id
  FROM public.users u
  WHERE u.role = 'patient'
  ORDER BY u.created_at
  LIMIT 1;

  IF p_id IS NULL THEN
    RAISE EXCEPTION 'No existing patient found. Create a patient in Aasra first.';
  END IF;

  -- Use ONLY games already present in your database.
  SELECT COALESCE(array_agg(game_id ORDER BY game_id), ARRAY[]::uuid[])
  INTO g_ids
  FROM public.cognitive_games
  WHERE active = true;

  -- 1. COGNITIVE PROGRESS
  -- 90 daily records for Memory / Attention / Recall / Pattern / Overall.
  INSERT INTO public.cognitive_progress
    (patient_id, date, memory_score, attention_score, recall_score,
     pattern_score, overall_score, trend)
  SELECT
    p_id,
    d::date,
    round((58 + n * 0.22 + sin(n * 0.70) * 5)::numeric, 1),
    round((62 + n * 0.18 + cos(n * 0.50) * 4)::numeric, 1),
    round((55 + n * 0.24 + sin(n * 0.45) * 6)::numeric, 1),
    round((60 + n * 0.20 + cos(n * 0.35) * 5)::numeric, 1),
    round((58.75 + n * 0.21 + sin(n * 0.30) * 3)::numeric, 1),
    CASE
      WHEN n >= 65 THEN 'improving'
      WHEN n >= 25 THEN 'stable'
      ELSE 'improving'
    END
  FROM (
    SELECT
      d,
      extract(day from (d::date - (current_date - 89)))::numeric AS n
    FROM generate_series(
      current_date - 89,
      current_date,
      interval '1 day'
    ) d
  ) x
  ON CONFLICT (patient_id, date) DO UPDATE SET
    memory_score = EXCLUDED.memory_score,
    attention_score = EXCLUDED.attention_score,
    recall_score = EXCLUDED.recall_score,
    pattern_score = EXCLUDED.pattern_score,
    overall_score = EXCLUDED.overall_score,
    trend = EXCLUDED.trend;

  -- 2. DAILY SUMMARIES
  -- Uses the existing Aasra daily summary fields.
  INSERT INTO public.daily_summaries
    (patient_id, date, app_used, cognitive_game_completed,
     mood_sleep_completed, movement_completed,
     medications_taken, medications_missed,
     tasks_completed, tasks_total, last_sync, trend, generated_at)
  SELECT
    p_id,
    d::date,
    true,
    (extract(dow from d) <> 0),
    true,
    (extract(dow from d) IN (1,3,5,6)),
    CASE WHEN extract(dow from d) IN (0,6) THEN 1 ELSE 2 END,
    CASE WHEN extract(day from d)::int % 13 = 0 THEN 1 ELSE 0 END,
    CASE WHEN extract(dow from d) IN (0,6) THEN 2 ELSE 3 END,
    3,
    d + interval '19 hours',
    CASE WHEN d::date >= current_date - 25 THEN 'improving' ELSE 'stable' END,
    d + interval '20 hours'
  FROM generate_series(
    current_date - 89,
    current_date,
    interval '1 day'
  ) d
  ON CONFLICT (patient_id, date) DO UPDATE SET
    app_used = EXCLUDED.app_used,
    cognitive_game_completed = EXCLUDED.cognitive_game_completed,
    mood_sleep_completed = EXCLUDED.mood_sleep_completed,
    movement_completed = EXCLUDED.movement_completed,
    medications_taken = EXCLUDED.medications_taken,
    medications_missed = EXCLUDED.medications_missed,
    tasks_completed = EXCLUDED.tasks_completed,
    tasks_total = EXCLUDED.tasks_total,
    last_sync = EXCLUDED.last_sync,
    trend = EXCLUDED.trend;

  -- 3. MOOD / SLEEP
  -- Uses the existing Aasra mood_sleep_logs table.
  INSERT INTO public.mood_sleep_logs
    (patient_id, date, sleep_quality, mood, notes, created_at)
  SELECT
    p_id,
    d::date,
    CASE
      WHEN extract(day from d)::int % 11 = 0 THEN 'poor'
      WHEN extract(day from d)::int % 4 = 0 THEN 'fair'
      ELSE 'good'
    END,
    CASE
      WHEN extract(day from d)::int % 17 = 0 THEN 'sad'
      WHEN extract(day from d)::int % 9 = 0 THEN 'anxious'
      WHEN extract(day from d)::int % 5 = 0 THEN 'tired'
      WHEN extract(day from d)::int % 3 = 0 THEN 'okay'
      ELSE 'happy'
    END,
    'Demo check-in for report testing',
    d + interval '9 hours'
  FROM generate_series(
    current_date - 89,
    current_date,
    interval '1 day'
  ) d
  ON CONFLICT DO NOTHING;

  -- 4. GAME SESSIONS
  -- Uses ONLY active cognitive games already in your database.
  -- If no existing active game is present, this section is skipped.
  IF array_length(g_ids, 1) IS NOT NULL THEN
    INSERT INTO public.game_sessions
      (patient_id, game_id, start_time, end_time,
       score, accuracy, difficulty, completion_status)
    SELECT
      p_id,
      g_ids[
        1 + (extract(day from (d::date - (current_date - 89)))::int
        % array_length(g_ids, 1))
      ],
      d + interval '10 hours',
      d + interval '10 hours 8 minutes',
      round((55 + n * 0.25 + sin(n * 0.60) * 7)::numeric, 1),
      round((55 + n * 0.25 + cos(n * 0.40) * 6)::numeric, 1),
      CASE
        WHEN extract(day from d)::int % 12 >= 9 THEN 'medium'
        ELSE 'easy'
      END,
      CASE
        WHEN extract(day from d)::int % 14 = 0 THEN 'abandoned'
        ELSE 'completed'
      END
    FROM (
      SELECT
        d,
        extract(day from (d::date - (current_date - 89)))::numeric AS n
      FROM generate_series(
        current_date - 89,
        current_date,
        interval '1 day'
      ) d
    ) x;
  END IF;

  -- 5. MOVEMENT SESSIONS
  -- Uses the existing Aasra movement_sessions table.
  INSERT INTO public.movement_sessions
    (patient_id, activity_name, start_time, end_time,
     accuracy, completion_status, notes)
  SELECT
    p_id,
    CASE
      WHEN extract(day from d)::int % 2 = 0
      THEN 'Morning Walk'
      ELSE 'Stretch & Move'
    END,
    d + interval '8 hours',
    d + interval '8 hours 15 minutes',
    round((70 + sin(extract(day from d) * 0.40) * 12)::numeric, 1),
    'completed',
    'Demo movement record for report testing'
  FROM generate_series(
    current_date - 89,
    current_date,
    interval '1 day'
  ) d
  WHERE extract(dow from d) IN (1,3,5,6);

END $$;

-- CHECK THE DATA AFTER RUNNING

SELECT
  'cognitive_progress' AS table_name,
  count(*) AS rows_added_or_present
FROM public.cognitive_progress
WHERE patient_id = (
  SELECT user_id
  FROM public.users
  WHERE role = 'patient'
  ORDER BY created_at
  LIMIT 1
)
AND date >= current_date - 89;

SELECT
  'daily_summaries' AS table_name,
  count(*) AS rows_added_or_present
FROM public.daily_summaries
WHERE patient_id = (
  SELECT user_id
  FROM public.users
  WHERE role = 'patient'
  ORDER BY created_at
  LIMIT 1
)
AND date >= current_date - 89;

SELECT
  'mood_sleep_logs' AS table_name,
  count(*) AS rows_added_or_present
FROM public.mood_sleep_logs
WHERE patient_id = (
  SELECT user_id
  FROM public.users
  WHERE role = 'patient'
  ORDER BY created_at
  LIMIT 1
)
AND date >= current_date - 89;

SELECT
  'game_sessions' AS table_name,
  count(*) AS rows_added_or_present
FROM public.game_sessions
WHERE patient_id = (
  SELECT user_id
  FROM public.users
  WHERE role = 'patient'
  ORDER BY created_at
  LIMIT 1
)
AND start_time::date >= current_date - 89;

SELECT
  'movement_sessions' AS table_name,
  count(*) AS rows_added_or_present
FROM public.movement_sessions
WHERE patient_id = (
  SELECT user_id
  FROM public.users
  WHERE role = 'patient'
  ORDER BY created_at
  LIMIT 1
)
AND start_time::date >= current_date - 89;
