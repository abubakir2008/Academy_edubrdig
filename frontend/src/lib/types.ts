/** Mirrors the pydantic schemas exposed by the backend services. */

export type Role =
  | "student"
  | "tutor"
  | "admin"
  | "super_admin"
  | "moderator"
  | "support_manager"
  | "content_manager"
  | "finance_manager";

export type User = {
  id: string;
  email: string;
  full_name: string | null;
  role: Role;
  is_active: boolean;
  is_verified?: boolean;
  referral_code: string;
  created_at?: string;
};

/** `/auth/admin/users` — same shape as `User` minus `referral_code`. */
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

export type TutorSummary = {
  user_id: string;
  headline: string | null;
  photo_url: string | null;
  country: string | null;
  native_language: string | null;
  languages_taught: string[];
  specializations: string[];
  experience_years: number;
  price_cents: number;
  trial_price_cents: number | null;
  currency: string;
  is_verified: boolean;
  rating: number;
  total_reviews: number;
  total_lessons: number;
};

export type WorkingHour = {
  id: string;
  weekday: number;
  start_time: string;
  end_time: string;
};

export type Certificate = {
  id: string;
  title: string;
  issued_by: string | null;
  year: number | null;
  file_url: string | null;
};

export type TutorDetail = TutorSummary & {
  description: string | null;
  video_url: string | null;
  is_active: boolean;
  working_hours: WorkingHour[];
  certificates: Certificate[];
};

export type Review = {
  id: string;
  author_id: string;
  tutor_id: string;
  lesson_id: string | null;
  rating: number;
  comment: string | null;
  created_at: string;
};

export type ReviewSummary = {
  tutor_id: string;
  average_rating: number;
  total_reviews: number;
};

export type Booking = {
  id: string;
  student_id: string;
  tutor_id: string;
  scheduled_start: string;
  scheduled_end: string;
  duration_minutes: number;
  is_trial: boolean;
  status: string;
  price_cents: number;
  currency: string;
  payment_id: string | null;
  lesson_id: string | null;
  package_id: string | null;
  cancel_reason: string | null;
  created_at: string;
};

export type Favorite = { id: string; tutor_id: string; created_at: string };

export type Progress = {
  id: string;
  subject: string;
  lessons_completed: number;
  hours_spent: number;
  notes: string | null;
  updated_at: string;
};

export type Student = {
  user_id: string;
  learning_goals: string | null;
  learning_languages: string[];
  level: string | null;
  favorites: Favorite[];
  progress: Progress[];
};

/** A submitted onboarding intake form — anonymous, staff follow up via `contact_*`. */
export type StudentLead = {
  id: string;
  subject: string | null;
  goal: string | null;
  date_of_birth: string | null;
  study_place: string | null;
  destination_country: string | null;
  full_name: string;
  contact_phone: string | null;
  contact_email: string | null;
  created_at: string;
};

/** Query parameters accepted by `GET /tutors`. */
export type TutorQuery = {
  q?: string;
  category?: string;
  language?: string;
  country?: string;
  min_price_cents?: number;
  max_price_cents?: number;
  min_rating?: number;
  min_experience?: number;
  native_speaker?: boolean;
  has_trial?: boolean;
  verified_only?: boolean;
  sort?: "rating" | "price_asc" | "price_desc" | "experience" | "reviews";
  limit?: number;
  offset?: number;
};

// --- Payments ---------------------------------------------------------

export type Refund = {
  id: string;
  amount_cents: number;
  reason: string | null;
  status: string;
  created_at: string;
};

export type Payment = {
  id: string;
  student_id: string;
  tutor_id: string;
  booking_id: string | null;
  quantity: number;
  amount_cents: number;
  currency: string;
  commission_rate: number;
  commission_cents: number;
  tutor_earnings_cents: number;
  status: string;
  gateway: string;
  created_at: string;
  refunds: Refund[];
};

export type CheckoutResult = {
  payment_id: string;
  status: string;
  amount_cents: number;
  currency: string;
  payment_url: string | null;
};

export type LessonPackage = {
  id: string;
  tutor_id: string;
  student_id: string;
  total_lessons: number;
  lessons_remaining: number;
  price_cents: number;
  currency: string;
  created_at: string;
};

// --- Wallet -------------------------------------------------------------

export type PayoutMethod = "bank_card" | "mobile_wallet" | "crypto" | "paypal";

export type Wallet = {
  tutor_id: string;
  balance_cents: number;
  currency: string;
};

export type WalletTransaction = {
  id: string;
  type: string;
  amount_cents: number;
  balance_after_cents: number;
  reference: string | null;
  description: string | null;
  created_at: string;
};

export type Withdrawal = {
  id: string;
  tutor_id: string;
  amount_cents: number;
  currency: string;
  method: PayoutMethod;
  destination: string | null;
  status: string;
  note: string | null;
  created_at: string;
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

// --- Support / disputes -----------------------------------------------

export type Ticket = {
  id: string;
  user_id: string;
  subject: string;
  status: string;
  priority: string;
  kind: "general" | "dispute";
  payment_id: string | null;
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

export type Complaint = {
  id: string;
  author_id: string;
  target_type: "tutor" | "review";
  target_id: string;
  reason: string;
  status: "open" | "reviewed" | "resolved" | "dismissed";
  resolution: string | null;
  created_at: string;
};

export type Document = {
  id: string;
  tutor_id: string;
  doc_type: string;
  file_url: string;
  status: string;
  note: string | null;
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

export type Category = {
  id: string;
  slug: string;
  name: string;
  group: string | null;
  seo_title: string | null;
  seo_description: string | null;
};

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
  categories: number;
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

// --- Lessons ------------------------------------------------------------

export type Homework = {
  id: string;
  lesson_id: string;
  title: string;
  description: string | null;
  due_date: string | null;
  status: "pending" | "submitted" | "graded";
  submission_text: string | null;
  grade: string | null;
  feedback: string | null;
};

export type Lesson = {
  id: string;
  booking_id: string | null;
  student_id: string;
  tutor_id: string;
  subject: string | null;
  scheduled_start: string;
  status: "scheduled" | "in_progress" | "completed" | "cancelled" | string;
  started_at: string | null;
  ended_at: string | null;
  duration_minutes: number;
  recording_url: string | null;
  tutor_notes: string | null;
  student_notes: string | null;
  homeworks: Homework[];
};

// --- Video -----------------------------------------------------------------

export type VerificationRequest = {
  id: string;
  tutor_id: string;
  kind: "profile" | "identity";
  status: "pending" | "approved" | "rejected";
  note: string | null;
};

export type VideoRoom = {
  room_id: string;
  token: string;
  join_url: string;
};
