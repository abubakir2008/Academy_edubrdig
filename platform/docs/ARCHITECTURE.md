# EduBridge — Architecture

EduBridge runs as **6 department services** — `identity`, `engagement`,
`content`, `backoffice`, `academics`, `calendar` — sized to fit a 4 GB / 13 GB
VPS. This document is the high-level map; see [SERVICES.md](SERVICES.md) for
the per-route index.

> The platform originally also had `catalog`, `scheduling`, and `finance`
> departments; those, and everything that only existed to serve them (tutor
> ratings, tutor verification, ticket disputes/refunds, subject categories),
> have been removed. `academics`/`calendar` are a later, unrelated addition
> (courses with one teacher and a student roster, and the lesson scheduling
> for them) — not a revival of the old ones.

## 1. Big picture

```
                        ┌──────────────┐
   mobile / web  ─────▶ │   Traefik    │   http://localhost/api/<prefix>/...
                        │  (gateway)   │   strips /api, routes by path prefix
                        └──────┬───────┘
   ┌──────────┬─────────┼──────────┬────────────┬───────────┐
   ▼          ▼         ▼          ▼            ▼           ▼
identity   engagement  content  backoffice   academics    calendar
   │          │         │          │            │           │
   └──────────┴─── one Postgres (schema per department) ─────┘
                              │
                    one Redis (Streams event bus,
                     tokens, rate-limit, realtime)
```

- **Gateway:** Traefik. One router per route prefix (`auth`, `chat`,
  `cms`, ...), each pointing at the department container that serves it.
  `PathPrefix(/api/<prefix>)` + `StripPrefix(/api)`. A department therefore
  namespaces its routes under each of its own prefixes (e.g. the `identity`
  container serves both `/auth/...` and `/users/...`).
- **Departments:** 6 FastAPI apps, each its own container, its own OpenAPI
  docs at `/docs`, all built from the **same image** (see `Dockerfile` —
  `$DEPARTMENT` selects which department's code runs).
- **Event bus:** Redis Streams. Departments publish domain events and consume
  the ones they care about — no synchronous department-to-department calls
  for anything that can be eventual.

## 2. Why departments, not one service per feature

The original 22-service layout needed ElasticSearch + Kafka + MongoDB +
RabbitMQ + 22 uvicorn containers — about 5.4 GB of RAM to start, more than a
4 GB host has. Consolidating containers alone wouldn't have fixed that; the
infrastructure that only existed to serve one query each had to go too:

- **Kafka → Redis Streams.** `shared/edubridge_shared/events.py`. Same
  consumer-group fan-out semantics, a fraction of the memory.
- **MongoDB → Postgres.** `chat`, `notifications`, `support` kept their
  document shapes but moved into their department's Postgres schema.
- **RabbitMQ → removed.** It was provisioned in the original compose file but
  no service ever imported it.
- **Many Postgres databases → 1 database, 1 schema per department.** Each
  department owns one schema (`identity`, `engagement`, `content`,
  `backoffice`, `academics`, `calendar`) instead of its modules each owning
  a database.
- **ElasticSearch** existed to index tutor listings; it, along with the
  `catalog`, `scheduling`, and `finance` departments it served, has since
  been removed entirely.

Departments group services by what they operate on together, so what used to
be a cross-service HTTP call is now an in-process function call. Genuinely
cross-department calls forward the caller's own JWT rather than a shared
service credential, so the target's normal per-user authorization still
applies — see `calendar`'s call into `academics` in §4a below, the first
real example of this.

## 3. Datastores

| Store | Used by |
|---|---|
| PostgreSQL (one DB, 6 schemas) | every department |
| Redis | tokens (db 0), rate-limit (db 2), realtime pub/sub (db 3), event bus (db 4) |
| MinIO | `content` department's `storage` module |

One `alembic upgrade head` runs per department (against its own schema) from
`entrypoint.sh` before that department serves traffic.

## 4. Identity & authentication

- **Identity department** (`auth` module) issues JWT **access** (short-lived)
  and **refresh** (long-lived, rotated, revocable via Redis) tokens.
- The token `sub` claim is the user id; the same id is the primary key of the
  user's profile in every department's tables (no cross-schema foreign keys —
  schemas are isolated on purpose, same as separate databases used to be).
- Every other department only **verifies** tokens, using the shared secret
  via `edubridge_shared.fastapi_auth.build_auth_dependencies`. No department
  calls identity at request time.
- OAuth (Apple): native mobile flow — the app performs sign-in and sends the
  `id_token`, which identity verifies against the provider's JWKS.

### Roles

`student`, `tutor`, `admin`, `super_admin`, `moderator`. Only `student`/`tutor`
are self-assignable at registration; staff roles are assigned by an admin.
Role checks use `require_roles(...)`.

## 4a. Courses & calendar

- **`academics`** (`courses` module) owns `Course` (title, description,
  `teacher_id` — exactly one `tutor`) and `Enrollment` (the course's roster,
  a.k.a. "group": many `student`s per course). Full CRUD, including
  assigning the teacher and managing the roster, is `super_admin`-only;
  `admin` can list/read but never mutates; a `tutor`/`student` only ever
  sees their own courses via `GET /courses/me`.
- **`calendar`** (`calendar` module) owns `Lesson` — a scheduled instance
  inside a course, with per-teacher conflict detection, weekly-recurring
  series (`series_id` groups the instances), and a `.ics` export
  (`GET /calendar/lessons/me.ics`, authorized by a `?token=` query param
  instead of a header — external calendar apps can't send one).
- Scheduling a lesson needs a same-request answer to "does this course
  exist, and is this tutor really its teacher?" — that can't wait for an
  event, so `calendar` calls `academics`' `GET /courses/{id}` synchronously,
  forwarding the caller's own JWT rather than a shared credential (see
  `calendar/app/modules/calendar/services/academics_client.py`). This is the
  platform's first real use of `edubridge_shared.clients.ServiceClient` —
  every other department only has the scaffolding for it, unused.
- `Lesson.teacher_id`/`course_id` are plain UUID columns, not foreign keys —
  same cross-department-FK policy as everywhere else in the platform.
- **Video calls (LiveKit)**: a lesson's call is a LiveKit room named
  `lesson-<id>`, unlike the Zoom OAuth integration this replaced — no
  per-tutor account to link and nothing that can fail on Zoom's end when
  scheduling, rescheduling or deleting a lesson. `GET /calendar/lessons/{id}/join`
  mints a short-lived access token for whoever's allowed to be in it (the
  lesson's own teacher, an enrolled student, or staff); minting is a
  self-signed JWT (`livekit-api`'s `AccessToken`/`VideoGrants`), not a
  network call. See `calendar/app/modules/calendar/services/livekit_client.py`.
- **Recordings**: if `RECORDINGS_S3_*` is configured, `POST /calendar/lessons`
  pre-creates the room (the one case where the room *is* set up ahead of the
  first join) with LiveKit auto-egress attached, so every lesson records
  itself from first join to last leave with no start/stop call from this
  platform — LiveKit Cloud's own egress workers upload the finished file
  straight to the bucket. `GET .../recordings` asks LiveKit which finished
  recordings exist for the room and signs each one for playback on request;
  nothing about a recording is persisted in our own database. See
  `calendar/app/modules/calendar/services/recordings.py`.

## 5. Event-driven choreography

Producers publish; consumers react autonomously (no frontend orchestration).
Each department consumes with its **own consumer group**, so an event fans
out to every interested department.

| Event | Producer | Consumers → effect |
|---|---|---|
| `auth.user_registered` | identity (auth) | backoffice (analytics, records to the event log) |

**Reliability characteristics:**
- Publishing is *best-effort*: a down Redis logs a warning and never breaks
  the HTTP request that triggered the event.
- Delivery is *at-least-once*, but a message is only acknowledged after every
  handler for it succeeds — not before, the way naive auto-commit consumers
  do it. A crash mid-handler leaves the message pending; it's picked back up
  by `XAUTOCLAIM` after an idle timeout, by this or another consumer in the
  same group.
- The bus marks each event id as seen (`SET NX`) so an ordinary redelivery is
  a no-op for every consumer.
- After 5 failed delivery attempts, an event is moved to a `<topic>:dead`
  stream and acknowledged, so one poison message can't block the stream
  forever.

Implementation: `shared/edubridge_shared/events.py` (`EventBus`, `Topics`);
each department has an `app/events.py` (the shared bus instance) and each
consuming module registers its handlers in its own `events.py`, all started
from the FastAPI lifespan (`app_factory.create_app(on_startup=..., on_shutdown=...)`).

## 6. Shared library (`edubridge_shared`)

Installed into the one image every department runs (`pip install /shared`):

- `config.py` — `DepartmentSettings`: Postgres/Redis connection config plus
  each department's own `db_schema`.
- `database.py` — `build_base(schema)` (schema-qualified declarative base),
  async engine/session factory, `UUIDMixin`, `TimestampMixin`.
- `security.py` — JWT create/decode; `fastapi_auth.py` — auth dependencies.
- `events.py` — Redis Streams event bus + topic names (see §5).
- `clients.py` — `ServiceClient` for cross-department calls (attaches
  `X-Internal-Secret`); `require_internal` guards any endpoint meant to be
  internal-only. Used for real by `calendar` → `academics` (§4a).
- `app_factory.py` — builds a consistent FastAPI app: logging, one
  `/<prefix>/health` per route prefix the department serves, lifespan hooks.
- `logging.py` — JSON logging; `schemas.py` — common response models;
  `realtime.py` — Redis pub/sub for WebSocket fan-out (chat, notifications).

## 7. Request routing recap

```
client → /api/chat/conversations              (Traefik: strip /api)
       → engagement container: GET /chat/...  (router prefix /chat,
                                                 module modules/chat)
```

## 8. Local run

```bash
cd platform
cp .env.example .env          # set JWT_SECRET_KEY, INTERNAL_SECRET for anything beyond local
docker compose up -d --build
curl http://localhost/api/auth/health
```

- Traefik dashboard: http://localhost:8080
- MailHog (dev SMTP catcher): http://localhost:8025
- MinIO console (profile `full`): http://localhost:9001
- Per-department Swagger UI: see `docker-compose.override.yml` for the port map.

## 9. Tests

`tests/` (pytest) covers the identity paths, academics' course CRUD/role
boundaries, and calendar's conflict-detection/recurrence/cross-department
authorization (the latter boots both `academics` and `calendar` in one test
process, wiring calendar's `ServiceClient` to academics' real app through an
in-process ASGI transport instead of a real socket — nothing is mocked, see
`tests/test_calendar_lessons.py`) — see `README.md`'s Testing section for
what's covered and `make test` to run it.

`scripts/e2e.py` is a broader live smoke test across every role and event
side effect, run against a fully up stack:

```bash
# through the gateway:
python scripts/e2e.py

# DIRECT mode, inside the docker network (bypasses Traefik):
docker run --rm --network platform_edubridge \
  -e DIRECT=1 -e JWT_SECRET="$(grep '^JWT_SECRET_KEY=' .env | cut -d= -f2)" \
  -v "$PWD/scripts:/scripts" \
  python:3.13-slim sh -c "pip install -q requests pyjwt && python /scripts/e2e.py"
```

## 10. Known gaps / next steps

- CI/CD (GitHub Actions running `make test` + `scripts/e2e.py`).
- Observability (Prometheus/Grafana/Loki) — currently JSON logs to stdout only.
- Kubernetes manifests, if the platform ever needs to scale past one VPS.
- SMS/Telegram/Push notification channels (email via MailHog/SMTP works today).
- Test coverage beyond the paths in `tests/`.
