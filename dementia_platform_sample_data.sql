-- SAMPLE DATA for Dementia Cognitive Assistance Platform
-- Run this AFTER running dementia_platform_supabase_schema.sql
-- Demo data only. Names, numbers and emails are fictional.

-- 5 users: 3 patients + 2 caretakers
insert into public.users (user_id, name, phone, email, role, language)
values
('00000000-0000-0000-0000-000000000001','Asha Sharma','9000000001','asha.demo@example.com','patient','Hindi'),
('00000000-0000-0000-0000-000000000002','Ramesh Das','9000000002','ramesh.demo@example.com','patient','Assamese'),
('00000000-0000-0000-0000-000000000003','Mira Devi','9000000003','mira.demo@example.com','patient','Bengali'),
('00000000-0000-0000-0000-000000000101','Neha Sharma','9000000101','neha.caretaker@example.com','caretaker','Hindi'),
('00000000-0000-0000-0000-000000000102','Arjun Das','9000000102','arjun.caretaker@example.com','caretaker','English');

-- Patient profiles
insert into public.patient_profiles
(patient_id, date_of_birth, gender, address, emergency_contact, dementia_stage, diagnosis_date, preferred_language, daily_routine, notes)
values
('00000000-0000-0000-0000-000000000001','1948-03-12','Female','Guwahati, Assam','9000000191','mild','2025-06-10','Hindi','Wake 7 AM; breakfast 8 AM; walk 10 AM; lunch 1 PM; medicine 8 PM','Enjoys music and family conversations.'),
('00000000-0000-0000-0000-000000000002','1944-11-25','Male','Shillong, Meghalaya','9000000192','moderate','2024-09-18','Assamese','Wake 6:30 AM; breakfast 8 AM; rest 2 PM; dinner 8 PM','Needs help with medication tracking.'),
('00000000-0000-0000-0000-000000000003','1951-07-08','Female','Agartala, Tripura','9000000193','mild','2025-02-21','Bengali','Wake 7 AM; breakfast 8 AM; afternoon rest; dinner 7:30 PM','Responds well to visual memory activities.');

-- Caretaker relationships
-- Neha looks after TWO patients: Asha + Ramesh
-- Arjun looks after ONE patient: Mira
insert into public.caretaker_patient
(relationship_id, patient_id, caretaker_id, relationship, is_primary, can_manage_medications, can_view_progress, can_receive_alerts)
values
('00000000-0000-0000-0000-000000001001','00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000101','Daughter',true,true,true,true),
('00000000-0000-0000-0000-000000001002','00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000101','Daughter',true,true,true,true),
('00000000-0000-0000-0000-000000001003','00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000000102','Son',true,true,true,true);

-- Sample medications
insert into public.medications
(medication_id, patient_id, medicine_name, dosage, quantity, frequency, start_date, instructions, status)
values
('00000000-0000-0000-0000-000000002001','00000000-0000-0000-0000-000000000001','Donepezil','5 mg',30,'Once daily','2026-09-01','Take after dinner','active'),
('00000000-0000-0000-0000-000000002002','00000000-0000-0000-0000-000000000002','Donepezil','10 mg',30,'Once daily','2026-08-15','Take after dinner','active'),
('00000000-0000-0000-0000-000000002003','00000000-0000-0000-0000-000000000003','Rivastigmine','3 mg',60,'Twice daily','2026-08-20','Take with food','active');

-- Medication schedules
insert into public.medication_schedule
(schedule_id, medication_id, time, days, dose, reminder_enabled, grace_period)
values
('00000000-0000-0000-0000-000000003001','00000000-0000-0000-0000-000000002001','20:00:00','daily',1,true,30),
('00000000-0000-0000-0000-000000003002','00000000-0000-0000-0000-000000002002','20:00:00','daily',1,true,30),
('00000000-0000-0000-0000-000000003003','00000000-0000-0000-0000-000000002003','08:00:00','daily',1,true,30),
('00000000-0000-0000-0000-000000003004','00000000-0000-0000-0000-000000002003','20:00:00','daily',1,true,30);

-- Cognitive games
insert into public.cognitive_games
(game_id, game_name, game_type, difficulty_level, language, description, active)
values
('00000000-0000-0000-0000-000000004001','Remember the Faces','memory','easy','Hindi','Match familiar faces with names.','true'),
('00000000-0000-0000-0000-000000004002','Pattern Path','pattern','easy','Assamese','Identify the next pattern in a sequence.','true'),
('00000000-0000-0000-0000-000000004003','Daily Recall','recall','medium','Bengali','Recall simple events from the day.','true');

-- Game sessions
insert into public.game_sessions
(session_id, patient_id, game_id, start_time, end_time, score, accuracy, difficulty, completion_status)
values
('00000000-0000-0000-0000-000000005001','00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000004001','2026-09-08 10:00:00+05:30','2026-09-08 10:06:00+05:30',82,82,'easy','completed'),
('00000000-0000-0000-0000-000000005002','00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000004002','2026-09-08 11:00:00+05:30','2026-09-08 11:08:00+05:30',68,68,'easy','completed'),
('00000000-0000-0000-0000-000000005003','00000000-0000-0000-0000-000000000003','00000000-0000-0000-0000-000000004003','2026-09-08 16:00:00+05:30','2026-09-08 16:07:00+05:30',91,91,'medium','completed');

-- Cognitive progress
insert into public.cognitive_progress
(progress_id, patient_id, date, memory_score, attention_score, recall_score, pattern_score, overall_score, trend)
values
('00000000-0000-0000-0000-000000006001','00000000-0000-0000-0000-000000000001','2026-09-08',82,78,80,75,79,'improving'),
('00000000-0000-0000-0000-000000006002','00000000-0000-0000-0000-000000000002','2026-09-08',65,62,68,70,66,'stable'),
('00000000-0000-0000-0000-000000006003','00000000-0000-0000-0000-000000000003','2026-09-08',91,88,92,89,90,'improving');

-- Memory assistance
insert into public.memory_assistance
(memory_id, patient_id, title, description, category, date_time, repeat_type, created_by, priority, status)
values
('00000000-0000-0000-0000-000000007001','00000000-0000-0000-0000-000000000001','Doctor appointment','Visit Dr. Mehta at 4 PM','appointment','2026-09-15 16:00:00+05:30','once','00000000-0000-0000-0000-000000000101','high','active'),
('00000000-0000-0000-0000-000000007002','00000000-0000-0000-0000-000000000002','Family call','Call daughter Neha','person','2026-09-09 18:00:00+05:30','daily','00000000-0000-0000-0000-000000000101','medium','active'),
('00000000-0000-0000-0000-000000007003','00000000-0000-0000-0000-000000000003','Granddaughter birthday','Wish Ananya happy birthday','event','2026-10-02 09:00:00+05:30','once','00000000-0000-0000-0000-000000000102','high','active');

-- General reminders
insert into public.reminders
(reminder_id, patient_id, title, description, reminder_type, date, time, repeat_pattern, status, created_by)
values
('00000000-0000-0000-0000-000000008001','00000000-0000-0000-0000-000000000001','Evening walk','Take a 15 minute walk','activity','2026-09-09','17:30:00','daily','pending','00000000-0000-0000-0000-000000000101'),
('00000000-0000-0000-0000-000000008002','00000000-0000-0000-0000-000000000002','Drink water','Drink one glass of water','other','2026-09-09','15:00:00','daily','pending','00000000-0000-0000-0000-000000000101'),
('00000000-0000-0000-0000-000000008003','00000000-0000-0000-0000-000000000003','Family call','Video call with family','activity','2026-09-09','19:00:00','daily','pending','00000000-0000-0000-0000-000000000102');

-- Medication logs demonstrate all three important states:
-- Taken = patient confirmed
-- Missed = no confirmation after escalation
-- Unknown = medicine may have been taken but patient did not update the app
insert into public.medication_logs
(log_id, schedule_id, patient_id, scheduled_time, action_time, status, confirmed_by, confirmation_method, reminder_count, alert_sent)
values
('00000000-0000-0000-0000-000000009001','00000000-0000-0000-0000-000000003001','00000000-0000-0000-0000-000000000001','2026-09-08 20:00:00+05:30','2026-09-08 20:05:00+05:30','taken','00000000-0000-0000-0000-000000000001','app',1,false),
('00000000-0000-0000-0000-000000009002','00000000-0000-0000-0000-000000003002','00000000-0000-0000-0000-000000000002','2026-09-08 20:00:00+05:30',null,'missed',null,null,3,true),
('00000000-0000-0000-0000-000000009003','00000000-0000-0000-0000-000000003003','00000000-0000-0000-0000-000000000003','2026-09-09 08:00:00+05:30',null,'unknown',null,null,2,false);

-- Emergency event for missed medicine
insert into public.emergency_events
(event_id, patient_id, event_type, detected_at, severity, action_taken, caretaker_notified, resolved)
values
('00000000-0000-0000-0000-000000010001','00000000-0000-0000-0000-000000000002','Missed medication','2026-09-08 21:00:00+05:30','medium','Caretaker notification triggered',true,false);

-- Sample SMS alert
insert into public.sms_alerts
(sms_id, patient_id, caretaker_id, message_type, message, delivery_status)
values
('00000000-0000-0000-0000-000000011001','00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000101','Medication','Ramesh has not confirmed his 8 PM medication. Please check on him.','delivered');

-- Sample offline sync record
insert into public.offline_sync
(sync_id, patient_id, device_id, data_type, data_id, action, sync_status, synced_at)
values
('00000000-0000-0000-0000-000000012001','00000000-0000-0000-0000-000000000003','DEVICE-MIRA-01','game_session','00000000-0000-0000-0000-000000005003','create','synced','2026-09-08 16:10:00+05:30');

-- Sample AI recommendations
insert into public.ai_recommendations
(recommendation_id, patient_id, recommendation_type, recommendation, reason, accepted, feedback)
values
('00000000-0000-0000-0000-000000013001','00000000-0000-0000-0000-000000000001','game','Try an easy face-name matching game today.','Recent memory performance is improving but remains lower than attention.','true','Patient enjoyed the activity.'),
('00000000-0000-0000-0000-000000013002','00000000-0000-0000-0000-000000000002','reminder','Add an additional medication confirmation reminder.','Recent medication reminder was missed.','true','Caretaker approved.'),
('00000000-0000-0000-0000-000000013003','00000000-0000-0000-0000-000000000003','activity','Use visual recall activities three times this week.','Visual recall scores are strong and can support continued engagement.','false',null);
