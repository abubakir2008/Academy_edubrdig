# EduBridge Route Index

One row per original route prefix (all 22 still work unchanged); grouped by
the department that now serves it. See `docs/ARCHITECTURE.md` for why they're
grouped this way and `README.md` for the event-flow diagram.

| Department | Prefix | Module store | Events |
|---|---|---|---|
| **identity** | `auth` | Postgres (`identity` schema) + Redis (refresh tokens) | pub: user_registered |
| | `users` | Postgres (`identity` schema) | — |
| **catalog** | `tutors` | Postgres (`catalog` schema) | sub: review.created, tutor.verified |
| | `students` | Postgres (`catalog` schema) | — |
| | `search` | same table as `tutors` (Postgres full-text, no separate store) | — |
| **scheduling** | `booking` | Postgres (`scheduling` schema) | pub: booking.created, booking.confirmed, booking.cancelled |
| | `calendar` | Postgres (`scheduling` schema) | — |
| | `lessons` | Postgres (`scheduling` schema) | pub: lesson.completed; sub: booking.confirmed |
| | `video` | Redis (ephemeral room state, own logical DB) | — |
| **finance** | `payments` | Postgres (`finance` schema) | pub: payment.succeeded, payment.refunded |
| | `wallet` | Postgres (`finance` schema) | sub: payment.succeeded |
| **engagement** | `chat` | Postgres (`engagement` schema) | — |
| | `notifications` | Postgres (`engagement` schema) | sub: payment.succeeded, booking.*, lesson.completed, review.created, tutor.verified |
| | `reviews` | Postgres (`engagement` schema) | pub: review.created |
| | `support` | Postgres (`engagement` schema) | — |
| **content** | `cms` | Postgres (`content` schema) | — |
| | `localization` | Postgres (`content` schema) | — |
| | `ai` | Postgres (`content` schema); Anthropic if `ANTHROPIC_API_KEY` is set, else local templates | — |
| | `storage` | MinIO | — |
| **backoffice** | `admin` | Postgres (`backoffice` schema) | — |
| | `moderation` | Postgres (`backoffice` schema) | pub: tutor.verified |
| | `analytics` | Postgres (`backoffice` schema) | sub: (all domain events) |

Notes on features added after the initial 7-department cut:
- `payments` also sells **lesson packages** (`POST /payments/packages/checkout`,
  discounted bundles of 5/10/20/40 lessons, paid in full upfront) — `booking`
  can redeem one credit per lesson via `POST /payments/packages/{id}/consume`
  instead of a fresh checkout (`BookingCreate.package_id`).
- `payments` also credits a flat referral bonus to whoever's `referral_code`
  a student registered with, on that student's first successful payment — see
  `_maybe_reward_referral` in `payments/api/routes/payments.py`. Every user
  gets a `referral_code` at registration (`identity`); `finance` looks up the
  referrer via `GET /auth/internal/referrer/{user_id}` (guarded by
  `require_internal`, not a user token — there's no logged-in user in that flow).
- `booking` rejects a second trial lesson between the same student/tutor pair
  (`crud.has_used_trial`) and exposes `GET /booking/{id}/ics` for a
  drop-into-any-calendar-app export.
- `video`'s `join_url` now points at Jitsi Meet (`JITSI_DOMAIN`, defaults to
  the free public `meet.jit.si` — no extra container, no RAM cost; point it at
  a self-hosted Jitsi stack later by changing one env var).
- `wallet` withdrawals now carry a `method` (`bank_card`/`mobile_wallet`/
  `crypto`/`paypal`) and a `destination` (the actual card/wallet/address).
- `moderation` exposes `GET /verification/me` so a tutor can see the outcome
  of their own submission — previously only staff could list requests at all.
- `support` tickets can be `kind="dispute"` (tied to a `payment_id`); staff
  resolve one via `POST /support/tickets/{id}/resolve`, which can issue the
  refund directly against `payments` using the staff member's own token.
- `chat` messages can carry `attachment_url`/`attachment_name` — the file
  itself goes through `storage`'s presigned-upload flow first (needs the
  `full` compose profile, i.e. MinIO, actually running).

Notes on what changed from the 22-service layout:
- `search` no longer has its own store — it queries the `tutors` table
  directly (same process, same department), full-text via a generated
  `tsvector` column. There's nothing to reindex.
- `chat`, `notifications`, `support` moved from MongoDB to Postgres — same
  document shapes, different engine.
- The event bus is Redis Streams, not Kafka — see
  `shared/edubridge_shared/events.py`.
- `video`'s Redis usage is unchanged (ephemeral join tokens / room state);
  it just moved into the `scheduling` container.
