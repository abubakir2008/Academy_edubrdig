# EduBridge Platform

Backend built on **FastAPI**. This repository is the monorepo for the
backend, shared code, and deployment configuration.

> Status: **6 department services** — `identity`, `engagement`, `content`,
> `backoffice`, `academics`, `calendar`. The platform originally also had
> `catalog` (tutor/student marketplace), `scheduling` (booking/lessons/video)
> and `finance` (payments/wallet) departments; those, and everything that
> only existed to serve them (tutor ratings, tutor verification, ticket
> disputes/refunds, subject categories), have been removed. `academics` and
> `calendar` are a later, separate addition — courses (one teacher, a
> student roster) and the lesson scheduling for them — not a revival of the
> old ones.

## Departments

| Department | Owns (former services) | Store |
|---|---|---|
| **identity** | auth, users | Postgres (`identity` schema) + Redis (refresh tokens) |
| **engagement** | chat, notifications, support | Postgres (`engagement` schema) + Redis (realtime pub/sub) |
| **content** | cms, localization, ai, storage | Postgres (`content` schema) + MinIO |
| **backoffice** | admin, analytics | Postgres (`backoffice` schema) |
| **academics** | courses | Postgres (`academics` schema) |
| **calendar** | calendar (lessons) | Postgres (`calendar` schema) |

Each department is a FastAPI app under `microservices/<department>/`, with
every former service living under `app/modules/<name>/`. Traefik routes
`/api/<prefix>/*` to the owning department's container (see
`deploy/docker/traefik/dynamic.yml`).

## Event-driven choreography

Departments never call each other synchronously for anything that can wait.
They publish **domain events** to Redis Streams (`shared/edubridge_shared/events.py`);
interested departments consume them and react on their own, each under its
own consumer group so every event fans out to all listeners. A handler is
only acked after it succeeds — a crash mid-handler leaves the message
pending and it gets reclaimed, instead of being silently dropped.

Currently the only published topic is `auth.user_registered`
(`Topics.USER_REGISTERED`), recorded by `backoffice`'s analytics event log.

One exception: scheduling a lesson needs a same-request answer ("does this
course exist, is this tutor really its teacher?"), so `calendar` calls
`academics` synchronously via `edubridge_shared.clients.ServiceClient` —
see "Service-to-service calls" below.

## Endpoints

Everything is namespaced under `/api/<prefix>`; every prefix also serves
`/<prefix>/health`. See `docs/SERVICES.md` for the full list.

## Architecture at a glance

```
                 ┌─────────────┐
  client ───────▶│   Traefik   │  http://localhost/api/<prefix>/...
                 │  (gateway)  │
                 └──────┬──────┘
    ┌──────────┬─────────┼──────────┬────────────┬───────────┐
    ▼          ▼         ▼          ▼            ▼           ▼
 identity  engagement  content  backoffice   academics    calendar
    all sharing one Postgres (schema per department) + one Redis
```

- **Gateway:** Traefik routes `/api/<prefix>/*` to the owning department's
  container (strips `/api`).
- **Identity** issues JWTs; every other department verifies them using the
  shared library (`edubridge_shared`).
- **Datastores:** one PostgreSQL, one Redis, optional MinIO (object storage)
  and MailHog (dev SMTP catcher) — see `docker-compose.yml`.
- **Service-to-service calls:** `edubridge_shared.clients.ServiceClient`
  forwards the caller's own JWT rather than using a shared service
  credential, so the target endpoint's normal authorization still applies,
  and attaches `X-Internal-Secret` (set `INTERNAL_SECRET` in `.env`) for any
  endpoint that's meant to be internal-only.

## Layout

```
platform/
├── docker-compose.yml         # full local stack (6 departments + postgres/redis/minio/mailhog/traefik)
├── Dockerfile                 # ONE image for every department (selected via $DEPARTMENT)
├── entrypoint.sh              # runs `alembic upgrade head` then uvicorn for $DEPARTMENT
├── requirements.txt           # one dependency set for every department
├── Makefile                   # dev shortcuts (make up / test / migrate D=<dept>)
├── .env.example                # copy to .env
├── shared/                    # edubridge_shared: config, database, events, clients, auth, logging
├── microservices/
│   ├── identity/                 # app/modules/{auth,users}/ + alembic/
│   ├── engagement/                # app/modules/{chat,notifications,support}/ + alembic/
│   ├── content/                   # app/modules/{cms,localization,ai,storage}/ + alembic/
│   ├── backoffice/                # app/modules/{admin,analytics}/ + alembic/
│   ├── academics/                 # app/modules/courses/ + alembic/
│   └── calendar/                  # app/modules/calendar/ + alembic/
├── tests/                     # pytest suite — see "Testing" below
└── deploy/
    └── docker/traefik/         # dynamic.yml, mapping each route prefix to its department
```

Inside a department, each former service lives under `app/modules/<name>/` with
its original `api/`, `crud/`, `models/`, `schemas/` structure untouched — only
its `core/config.py`, `db/`, and `deps.py` are now thin re-exports of the
department's shared settings, engine, and JWT dependencies.

## Quick start

```bash
cd platform
cp .env.example .env          # then edit JWT_PRIVATE_KEY/JWT_PUBLIC_KEY, INTERNAL_SECRET, etc.
docker compose up -d --build  # or: make up
```

Check it is alive:

```bash
curl http://localhost/api/auth/health
```

### Try the Auth flow (identity department)

There is no self-service registration — every account is admin-created (see
`scripts/seed_full.py` for how the first admin gets bootstrapped without
already having one):

```bash
# Admin creates an account; the response includes a freshly generated password.
curl -X POST http://localhost/api/auth/admin/users \
  -H "Authorization: Bearer <ADMIN_ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"email":"stud@example.com","full_name":"Ann","role":"student"}'

# Login -> returns access_token + refresh_token
curl -X POST http://localhost/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"stud@example.com","password":"<PASSWORD FROM THE CREATE RESPONSE>"}'

# Current user
curl http://localhost/api/auth/me -H "Authorization: Bearer <ACCESS_TOKEN>"
```

Interactive docs for any department: `docker-compose.override.yml` publishes
each department's Swagger UI on its own port (e.g. `http://localhost:8001/docs`
for identity) — see that file for the full port map.

## Testing

```bash
make test
```

Runs the pytest suite (`tests/`) against real Postgres and Redis (started via
`docker compose up -d postgres redis` if not already running), executed
inside a container on the compose network. Each test gets its own disposable
Postgres schema (`<department>_test_<random>`), created straight from that
department's SQLAlchemy models and dropped afterward — no mocked database.

Coverage:
- **identity**: admin-create / login / refresh / me, duplicate email, wrong
  password, a reset password invalidates the old one, non-admins can't
  create accounts, a plain `admin` can't create or promote a `super_admin`.
- **academics**: super_admin has full course CRUD; admin can list/read but
  never mutate; tutor/student only ever see their own courses.
- **calendar**: a tutor can only schedule inside their own course (verified
  against a *real* academics instance — see `test_calendar_lessons.py`),
  double-booking the same slot 409s, weekly recurrence creates every
  instance, deleting a series removes all of them.
- **engagement**: push-token register/unregister, an internal-only
  reminder/notification shows up for its user, a chat message notifies the
  other participant (not the sender), `POST /notifications` is staff-only.
- **content**: `presign-download` is scoped to the caller's own object
  (staff can reach any object).
- **backoffice**: `POST /analytics/events` always records the caller's own
  `user_id`, never a client-supplied one.

For a full live smoke test against every endpoint (not just these focused
cases), bring up the whole stack and run `python scripts/e2e.py`
(`DIRECT=1` to bypass the gateway and hit each department container by name).

## Roadmap

1. ✅ Monorepo, shared lib, gateway, full-stack compose.
2. ✅ Consolidated into department services sharing one Postgres (schema per
   department) and one Redis; ElasticSearch/Kafka/MongoDB/RabbitMQ removed.
3. ✅ Event-driven choreography (Redis Streams, at-least-once with ack-after-success).
4. ✅ Removed the `catalog`/`scheduling`/`finance` departments and every
   feature that only existed to serve them (tutor ratings, tutor
   verification, ticket disputes/refunds, subject categories).
5. ✅ pytest suite for the identity paths above.
6. ✅ Added `academics` (courses: one teacher, a student roster) and
   `calendar` (lesson scheduling: conflict detection, weekly recurrence,
   `.ics` export) — the platform's first real cross-department synchronous
   call (`calendar` → `academics`).
7. ✅ Video calls moved from per-tutor Zoom OAuth to embedded LiveKit; lesson
   recording moved from LiveKit's paid Egress to a dedicated
   `lesson-recorder` bot (`platform/lesson-recorder/`) uploading to a
   self-hosted/S3-compatible bucket, streamed back through calendar's own
   API — see `docs/SERVICES.md`'s recordings note, not LiveKit Egress.
8. ✅ JWT moved from a shared HS256 secret to RS256 (identity holds the
   private key and signs; every department verifies with the public key
   alone) — contains the blast radius of a compromised department.
9. ✅ CI gate: `deploy-backend.yml` now runs this pytest suite before any
   deploy touches the server (was: straight `git pull` + restart).
10. ✅ Push notifications (Expo push API): device-token registration, a
    lesson-start reminder (teacher only — reminding enrolled students needs
    a tokenless roster read `academics` doesn't expose yet), and a
    new-chat-message push, alongside the existing in-app/WebSocket delivery.
11. Remaining: k8s manifests (if ever needed beyond a single VPS),
    observability (Prometheus/Grafana/Loki), SMS/Telegram notification
    channels, student-facing lesson reminders, broader test coverage.
