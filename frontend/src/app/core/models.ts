export type VolunteerStatus = 'active' | 'inactive';
export type ChildStatus = 'active' | 'inactive' | 'visitor' | 'left';
export type PhotoConsent = 'granted' | 'denied' | 'not_recorded';
export type NoClassDayKind = 'holiday' | 'closure' | 'other';
export type AttendanceStatus = 'present' | 'absent';
export type UserRole = 'admin' | 'leader' | 'parent';

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface MinistryYear {
  id: string;
  label: string;
  start_date: string;
  end_date: string;
  meeting_weekdays: number[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface NoClassDay {
  id: string;
  ministry_year_id: string;
  date: string;
  name: string;
  kind: NoClassDayKind;
  created_at: string;
  updated_at: string;
}

export interface Volunteer {
  id: string;
  first_name: string;
  last_name: string;
  phone: string;
  email: string | null;
  joined_on: string | null;
  status: VolunteerStatus;
  created_at: string;
  updated_at: string;
}

export interface VolunteerSummary {
  id: string;
  first_name: string;
  last_name: string;
  phone: string;
  status: VolunteerStatus;
}

export interface Household {
  id: string;
  name: string | null;
  address: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Guardian {
  id: string;
  household_id: string | null;
  first_name: string;
  last_name: string;
  phone: string;
  email: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface GuardianSummary {
  id: string;
  first_name: string;
  last_name: string;
  phone: string;
  email: string | null;
  relationship: string;
  is_primary: boolean;
  is_emergency: boolean;
}

export interface ChildGuardian {
  id: string;
  child_id: string;
  guardian_id: string;
  relationship: string;
  is_primary: boolean;
  is_emergency: boolean;
  guardian: Guardian;
  created_at: string;
  updated_at: string;
}

export interface ChildSummary {
  id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  allergies: string | null;
  medical_notes: string | null;
  photo_consent: PhotoConsent;
  status: ChildStatus;
}

export interface Child extends ChildSummary {
  household_id: string | null;
  grade: string | null;
  joined_on: string | null;
  notes: string | null;
  guardian_count: number;
  created_at: string;
  updated_at: string;
}

export interface ClassGroup {
  id: string;
  ministry_year_id: string;
  name: string;
  age_band: string;
  age_min: number | null;
  age_max: number | null;
  lead_volunteer_id: string | null;
  room: string | null;
  capacity: number | null;
  curriculum: string | null;
  created_at: string;
  updated_at: string;
}

export interface Enrollment {
  id: string;
  class_id: string;
  child_id: string;
  start_date: string;
  end_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface RosterEntry extends Enrollment {
  child: ChildSummary;
}

export interface ResourceLink {
  label: string;
  url: string;
}

export interface ClassSession {
  id: string;
  class_id: string;
  date: string;
  start_time: string;
  end_time: string;
  topic: string | null;
  notes: string | null;
  content_markdown: string | null;
  resources: ResourceLink[];
  created_at: string;
  updated_at: string;
}

export interface SessionGenerateResult {
  created: number;
  skipped: number;
  session_ids: string[];
}

export interface SessionVolunteer {
  id: string;
  class_session_id: string;
  volunteer_id: string;
  volunteer: VolunteerSummary;
}

export interface SessionVolunteers {
  class_session_id: string;
  volunteers: SessionVolunteer[];
}

export interface AttendanceEntry {
  child: ChildSummary;
  guardians: GuardianSummary[];
  status: AttendanceStatus | null;
  note: string | null;
  recorded: boolean;
}

export interface VisitorAttendance {
  id: string;
  visitor_name: string;
  status: AttendanceStatus;
  note: string | null;
}

export interface AttendanceSummary {
  present: number;
  absent: number;
  not_recorded: number;
  recorded: number;
  visitors_present: number;
  visitors_absent: number;
  rate: number | null;
}

export interface SessionAttendance {
  session: ClassSession;
  entries: AttendanceEntry[];
  visitors: VisitorAttendance[];
  summary: AttendanceSummary;
}

export interface AttendanceReport {
  from_date: string;
  to_date: string;
  class_id: string | null;
  child_id: string | null;
  present: number;
  absent: number;
  not_recorded: number;
  recorded: number;
  visitors_present: number;
  visitors_absent: number;
  rate: number | null;
}

export interface NotSeenEntry {
  child: ChildSummary;
  last_present_on: string | null;
  missed_sessions: number;
}

export interface NotSeenReport {
  since: string;
  class_id: string | null;
  items: NotSeenEntry[];
  total: number;
}

export interface DashboardCounts {
  children: number;
  volunteers: number;
  classes: number;
}

export interface DashboardSession {
  id: string;
  class_id: string;
  class_name: string;
  date: string;
  start_time: string;
  end_time: string;
  topic: string | null;
  volunteers: number;
}

export interface Dashboard {
  active_year: MinistryYear | null;
  today: string;
  counts: DashboardCounts;
  todays_sessions: DashboardSession[];
  attendance_recorded_today: number;
  not_seen_recently: number;
}

export interface ClassMapping {
  source_class_id: string;
  target_class_id: string;
}

export interface PromotionAssignment {
  child_id: string;
  child_name: string;
  source_class_id: string;
  source_class_name: string;
  target_class_id: string;
  target_class_name: string;
  age_at_target_start: number;
  target_age_band: string;
}

export interface PromotionUnmatched {
  child_id: string;
  child_name: string;
  source_class_id: string | null;
  source_class_name: string | null;
  reason: string;
}

export interface PromotionAlreadyEnrolled {
  child_id: string;
  child_name: string;
  target_class_id: string;
  target_class_name: string;
}

export interface PromotionCounts {
  assign: number;
  unmatched: number;
  already_enrolled: number;
}

export interface PromotionPreview {
  assignments: PromotionAssignment[];
  unmatched: PromotionUnmatched[];
  already_enrolled: PromotionAlreadyEnrolled[];
  counts: PromotionCounts;
}

export interface PromotionApplyResult {
  created: number;
  skipped: number;
  enrollment_ids: string[];
}

export interface AuditLog {
  id: string;
  actor_user_id: string | null;
  actor_email: string | null;
  action: string;
  entity_type: string;
  entity_id: string;
  changes: Record<string, unknown>;
  created_at: string;
}
