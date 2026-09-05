/** Mirrors the pydantic schemas exposed by the backend services. */

export type Role = "student" | "tutor" | "admin" | "super_admin" | "moderator";

export type User = {
  id: string;
  email: string;
  full_name: string | null;
  role: Role;
  is_active: boolean;
  is_verified?: boolean;
  created_at?: string;
};

export type AdminUser = {
  id: string;
  email: string;
  full_name: string | null;
  role: Role;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
};

export type AdminUserCreated = { user: AdminUser; password: string };
export type PasswordIssued = { password: string };

/** `GET /users/{id}` / `GET /users/batch` — name + photo, resolved with a
 * fallback to the account's given name when nobody's ever saved Settings. */
export type Profile = {
  user_id: string;
  full_name: string | null;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
};

// --- Chat -----------------------------------------------------------------

export type Conversation = {
  id: string;
  participants: string[];
  last_text: string | null;
  last_message_at: string | null;
};

export type ChatMessage = {
  id: string;
  sender_id: string;
  text: string;
  attachment_url: string | null;
  attachment_name: string | null;
  created_at: string;
  read_by: string[];
};

// --- Support -------------------------------------------------------------

export type Ticket = {
  id: string;
  user_id: string;
  subject: string;
  status: string;
  priority: string;
  created_at: string;
  updated_at: string;
};

export type TicketMessage = {
  id: string;
  sender_id: string;
  text: string;
  is_staff: boolean;
  created_at: string;
};

// --- CMS / localization ------------------------------------------------

export type Article = {
  id: string;
  slug: string;
  type: "blog" | "faq" | "page" | "policy" | "landing";
  title: string;
  body: string;
  published: boolean;
  author_id: string | null;
  seo_title: string | null;
  seo_description: string | null;
  created_at: string;
  updated_at: string;
};

export type Language = { code: string; name: string; is_active: boolean };

// --- Admin / analytics ---------------------------------------------------

export type SystemSetting = { key: string; category: string; value: Record<string, unknown> };

export type AdminAction = {
  id: string;
  admin_id: string;
  action: string;
  target_type: string | null;
  target_id: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
};

export type AdminDashboard = {
  settings: number;
  admin_actions: number;
  note: string;
};

export type AnalyticsSummary = {
  date_from: string;
  date_to: string;
  total_events: number;
  unique_users: number;
  revenue_cents: number;
};

// --- Notifications ----------------------------------------------------

export type AppNotification = {
  id: string;
  type: string;
  title: string;
  body: string | null;
  channel: string;
  read: boolean;
  created_at: string;
};

// --- Courses (academics) -------------------------------------------------

export type Course = {
  id: string;
  title: string;
  description: string | null;
  teacher_id: string | null;
  category_id: string | null;
  created_at: string;
  updated_at: string;
};

/** `GET /courses/{id}` — a course plus its roster ("group"). */
export type CourseDetail = Course & { student_ids: string[] };

// --- Categories (academics) ----------------------------------------------

export type Category = {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
};

// --- Calendar --------------------------------------------------------------

/** "missed" is never stored — the backend computes it on every read for a
 * "scheduled" lesson whose scheduled_end is already in the past. */
export type LessonStatus = "scheduled" | "completed" | "cancelled" | "missed";

export type Lesson = {
  id: string;
  course_id: string;
  teacher_id: string;
  series_id: string | null;
  /** null for a whole-course-roster lesson; set for a 1:1 lesson. */
  student_id: string | null;
  scheduled_start: string;
  scheduled_end: string;
  status: LessonStatus;
  title: string | null;
  description: string | null;
  created_at: string;
};

// --- Video calls (LiveKit) -------------------------------------------------

/** `GET /calendar/lessons/{id}/join` — everything needed to connect to a
 * lesson's LiveKit room. Minted fresh per request, never stored. */
export type LessonJoin = { livekit_url: string; token: string; room: string };

/** `GET /calendar/lessons/{id}/recordings` — one finished recording of a
 * call session inside this lesson's room (there can be more than one if the
 * call was left and rejoined). */
export type Recording = {
  object_name: string;
  url: string;
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;
};

// --- Homework (calendar) ---------------------------------------------------

export type HomeworkStatus = "assigned" | "submitted" | "graded";

export type Homework = {
  id: string;
  lesson_id: string;
  course_id: string;
  teacher_id: string;
  student_id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  status: HomeworkStatus;
  submission_url: string | null;
  submission_note: string | null;
  submitted_at: string | null;
  grade: number | null;
  comment: string | null;
  graded_at: string | null;
  created_at: string;
};

// --- Leads (public "leave a request" intake, backoffice) ------------------

export type LeadStatus = "new" | "contacted" | "closed";

export type Lead = {
  id: string;
  subject: string | null;
  goal: string | null;
  date_of_birth: string | null;
  study_place: string | null;
  destination_country: string | null;
  full_name: string;
  contact_phone: string | null;
  contact_email: string | null;
  preferred_tutor_id: string | null;
  status: LeadStatus;
  created_at: string;
};

// --- Tutors (identity, public "our teachers" page) -------------------------

export type TutorCard = {
  user_id: string;
  full_name: string | null;
  avatar_url: string | null;
  experience_years: number | null;
  bio_short: string | null;
  languages: string[] | null;
  category_ids: string[] | null;
};

/** `GET /users/tutors/{id}` — a tutor card plus the full write-up. */
export type TutorDetail = TutorCard & { bio_full: string | null };
