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
- `calendar` also owns Zoom account linking: `GET /calendar/zoom/connect`
  (tutor-only, returns an authorize URL), `GET /calendar/zoom/callback`
  (public — Zoom's browser redirect lands here), `GET /calendar/zoom/status`,
  `DELETE /calendar/zoom`. Every tutor links their **own** Zoom account
  (OAuth `authorization_code`, not a shared platform login); every
  `POST /calendar/lessons` creates one real Zoom meeting per lesson instance
  on that teacher's account and fails outright (409) if they haven't linked
  one yet — see `calendar/app/modules/calendar/services/zoom_client.py`.
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
