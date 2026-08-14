# EduBridge Route Index

One row per route prefix, grouped by the department that serves it. See
`docs/ARCHITECTURE.md` for why they're grouped this way and `README.md` for
the event-flow summary.

| Department | Prefix | Module store | Events |
|---|---|---|---|
| **identity** | `auth` | Postgres (`identity` schema) + Redis (refresh tokens) | pub: user_registered |
| | `users` | Postgres (`identity` schema) | — |
| **engagement** | `chat` | Postgres (`engagement` schema) | — |
| | `notifications` | Postgres (`engagement` schema) | — |
| | `support` | Postgres (`engagement` schema) | — |
| **content** | `cms` | Postgres (`content` schema) | — |
| | `localization` | Postgres (`content` schema) | — |
| | `ai` | Postgres (`content` schema); Anthropic if `ANTHROPIC_API_KEY` is set, else local templates | — |
| | `storage` | MinIO | — |
| **backoffice** | `admin` | Postgres (`backoffice` schema) | — |
| | `analytics` | Postgres (`backoffice` schema) | sub: user_registered |
| | `leads` | Postgres (`backoffice` schema) | — |
| **academics** | `courses` | Postgres (`academics` schema) | — |
| **calendar** | `calendar` | Postgres (`calendar` schema) | — |

Notes:
- `courses` (a course has exactly one `tutor` as teacher and a roster —
  "group" — of `student` enrollments) and `calendar` (lessons scheduled
  inside a course, with weekly recurrence, per-teacher conflict detection,
  and a `.ics` export) are a fresh pair of departments, not a revival of the
  old `catalog`/`scheduling` ones below. `calendar` calls `courses`
  synchronously (forwarding the caller's own JWT) to confirm a tutor really
  teaches the course they're scheduling into — see
  `calendar/app/modules/calendar/services/academics_client.py`, the
  platform's first real use of `edubridge_shared.clients.ServiceClient`.
- `calendar` also owns video calls: `GET /calendar/lessons/{id}/join`
  mints a LiveKit access token for whoever's allowed to be in that lesson
  (its teacher, an enrolled student, or staff) — a self-signed JWT, no
  network call and nothing to link or persist ahead of time, unlike the
  Zoom OAuth integration this replaced. The room itself is just
  `lesson-<id>`; it starts existing the moment someone's token lets them
  connect. See `calendar/app/modules/calendar/services/livekit_client.py`.
- `calendar` also owns recordings: every lesson's room is created with
  LiveKit auto-egress attached, so it's recorded automatically from the
  first join to the last leave, uploaded straight from LiveKit Cloud's own
  infrastructure to an S3-compatible bucket (Cloudflare R2) — this
  department never handles the video bytes. `GET /calendar/lessons/{id}/recordings`
  mints short-lived presigned URLs to whoever's allowed to see the lesson;
  `DELETE .../recordings/{object_name}` (the lesson's own teacher or staff)
  removes one from the bucket. See
  `calendar/app/modules/calendar/services/recordings.py`. Optional — a
  server with no `RECORDINGS_S3_*` configured just never records, silently.
- `leads`: `POST /leads` is the one public, unauthenticated write in this
  department — it's how a visitor with no account yet (there's no
  self-registration) reaches staff, from the marketing site's `/onboarding`
  form. `GET /leads` / `PUT /leads/{id}/status` are admin/super_admin only.
- `academics` auto-creates chat conversations (student↔teacher,
  student↔every super_admin) whenever a student is enrolled or a teacher is
  assigned to a course with an existing roster — best-effort calls to
  `engagement`'s internal-only `POST /chat/conversations/internal`
  (`courses/services/chat_client.py`), so nobody has to start the
  conversation manually before they can talk.
- `chat` messages can carry `attachment_url`/`attachment_name` — the file
  itself goes through `storage`'s presigned-upload flow first (needs the
  `full` compose profile, i.e. MinIO, actually running).
- `chat`, `notifications`, `support` moved from MongoDB to Postgres — same
  document shapes, different engine.
- The event bus is Redis Streams, not Kafka — see
  `shared/edubridge_shared/events.py`.
- The `catalog` (tutors/students/search), `scheduling`
  (booking/calendar/lessons/video), and `finance` (payments/wallet)
  departments have been removed, along with everything that only existed to
  serve them: `engagement`'s tutor-rating module (`reviews`), `support`'s
  dispute/refund flow, and `backoffice`'s tutor-verification queue and
  subject `categories`.
