# EduBridge Platform

Backend for an online tutoring marketplace (a Preply-style platform), built on
**FastAPI**. This repository is the monorepo for the backend, shared code, and
deployment configuration.

> Status: **7 department services**, consolidated from an earlier 22-microservice
> layout so the whole stack fits a 4 GB / 13 GB VPS. Every original route prefix
> still works exactly as before (`http://localhost/api/<prefix>/...`) — only which
> container serves it changed. See "Why 7 departments, not 22" below.

## Why 7 departments, not 22

22 independently-deployed services made sense on paper but not on this host:
ElasticSearch + Kafka + MongoDB + RabbitMQ + 22 uvicorn containers needed
~5.4 GB of RAM just to start, more than the box has. The fix wasn't just
merging containers — it meant removing the infrastructure that only existed to
serve one query each:

| Removed | Replaced by |
|---|---|
| ElasticSearch (tutor search index) | Postgres full-text search — a generated `tsvector` column on the `tutors` table itself (see `catalog/app/modules/tutors/models/tutor.py`). A tutor row update *is* the search update now; there's nothing to reindex. |
| Kafka (event bus) | Redis Streams (`shared/edubridge_shared/events.py`) — consumer groups, manual ack after the handler succeeds (not before), stalled-message reclaim, and a dead-letter stream after repeated failures. |
| MongoDB (chat, notifications, support) | Postgres, same department schema as everything else those modules needed anyway. |
| RabbitMQ | Nothing — it was provisioned but never imported by any service. |
| 15 separate Postgres databases | One database, one schema per department (`identity`, `catalog`, `scheduling`, `finance`, `engagement`, `content`, `backoffice`). |

Departments group the original 22 services by what they actually do together,
not by table:

| Department | Owns (former services) | Store |
|---|---|---|
| **identity** | auth, users | Postgres (`identity` schema) + Redis (refresh tokens) |
| **catalog** | tutors, students, search | Postgres (`catalog` schema) — search is full-text over `tutors` |
| **scheduling** | booking, calendar, lessons, video | Postgres (`scheduling` schema) + Redis (video rooms) |
| **finance** | payments, wallet | Postgres (`finance` schema) |
| **engagement** | chat, notifications, reviews, support | Postgres (`engagement` schema) + Redis (realtime pub/sub) |
| **content** | cms, localization, ai, storage | Postgres (`content` schema) + MinIO |
| **backoffice** | admin, moderation, analytics | Postgres (`backoffice` schema) |

Every one of the original 22 route prefixes (`/auth`, `/tutors`, `/booking`, ...)
still resolves — Traefik just points each prefix at its department's container
instead of its own (see `deploy/docker/traefik/dynamic.yml`). The frontend and
any external caller needed zero changes.

## Event-driven choreography (services work without the frontend)

Departments never call each other synchronously for anything that can wait.
They publish **domain events** to Redis Streams; interested departments
consume them and react on their own, each under its own consumer group so
every event fans out to all listeners. A handler is only acked after it
succeeds — a crash mid-handler leaves the message pending and it gets
reclaimed, instead of being silently dropped.

```
payment.succeeded ─┬─▶ wallet         (credit the tutor's balance, idempotent)
                   ├─▶ notifications  (notify student + tutor)
                   └─▶ analytics      (record revenue)

booking.confirmed ─┬─▶ lessons        (auto-create the lesson, idempotent)
                   ├─▶ notifications
                   └─▶ analytics

lesson.completed  ─┬─▶ notifications  (ask the student for a review)
                   └─▶ analytics

review.created    ─┬─▶ tutors         (update rating + count)
                   ├─▶ notifications
                   └─▶ analytics

tutor.verified    ─┬─▶ tutors         (set is_verified)
                   ├─▶ notifications
                   └─▶ analytics

booking.created/cancelled ─▶ notifications + analytics
```

Example of the autonomous flow: a student calls **one** endpoint
`POST /api/payments/checkout` → the tutor's wallet is credited, both users get
notifications, and revenue is logged — all without any further client calls.

## Endpoints

Everything is namespaced under `/api/<prefix>`; every prefix also serves
`/<prefix>/health`. 126 endpoints across the 22 original prefixes; see
`docs/SERVICES.md` for the full list.

## Architecture at a glance

```
                 ┌─────────────┐
  client ───────▶│   Traefik   │  http://localhost/api/<prefix>/...
                 │  (gateway)  │
                 └──────┬──────┘
    ┌──────────┬─────────┼──────────┬────────────┬─────────┬────────────┐
    ▼          ▼         ▼          ▼            ▼         ▼            ▼
 identity   catalog  scheduling  finance     engagement  content   backoffice
    all sharing one Postgres (schema per department) + one Redis
```

- **Gateway:** Traefik routes `/api/<prefix>/*` to the owning department's
  container (strips `/api`).
- **Identity** issues JWTs; every other department verifies them using the
  shared library (`edubridge_shared`).
- **Datastores:** one PostgreSQL, one Redis, optional MinIO (object storage)
  and MailHog (dev SMTP catcher) — see `docker-compose.yml`.
- **Service-to-service calls** (the few that remain — e.g. reviews verifying a
  lesson with scheduling) forward the caller's own JWT rather than using a
  shared service credential, so the target endpoint's normal authorization
  still applies. `edubridge_shared.clients.ServiceClient` also attaches
  `X-Internal-Secret` (set `INTERNAL_SECRET` in `.env`) for any future
  endpoint that's meant to be internal-only.

## Layout

```
platform/
├── docker-compose.yml         # full local stack (7 departments + postgres/redis/minio/mailhog/traefik)
├── Dockerfile                 # ONE image for every department (selected via $DEPARTMENT)
├── entrypoint.sh              # runs `alembic upgrade head` then uvicorn for $DEPARTMENT
├── requirements.txt           # one dependency set for every department
├── Makefile                   # dev shortcuts (make up / test / migrate D=<dept>)
├── .env.example                # copy to .env
├── shared/                    # edubridge_shared: config, database, events, clients, auth, logging
├── microservices/
│   ├── identity/               # app/modules/{auth,users}/ + alembic/
│   ├── catalog/                # app/modules/{tutors,students,search}/ + alembic/
│   ├── scheduling/              # app/modules/{booking,calendar,lessons,video}/ + alembic/
│   ├── finance/                 # app/modules/{payments,wallet}/ + alembic/
│   ├── engagement/               # app/modules/{chat,notifications,reviews,support}/ + alembic/
│   ├── content/                  # app/modules/{cms,localization,ai,storage}/ + alembic/
│   └── backoffice/               # app/modules/{admin,moderation,analytics}/ + alembic/
├── tests/                     # pytest suite — see "Testing" below
└── deploy/
    └── docker/traefik/         # dynamic.yml, generated by mapping each of the
                                 # 22 route prefixes to its department
```

Inside a department, each former service lives under `app/modules/<name>/` with
its original `api/`, `crud/`, `models/`, `schemas/` structure untouched — only
its `core/config.py`, `db/`, and `deps.py` are now thin re-exports of the
department's shared settings, engine, and JWT dependencies.

## Quick start

```bash
cd platform
cp .env.example .env          # then edit JWT_SECRET_KEY, INTERNAL_SECRET, etc.
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

Coverage focuses on the money- and integrity-sensitive paths:
- **identity**: admin-create / login / refresh / me, duplicate email, wrong
  password, a reset password invalidates the old one, non-admins can't
  create accounts.
- **scheduling**: booking is rejected outside a tutor's configured calendar
  hours, and still allowed when no calendar is configured yet.
- **finance**: crediting a tutor's wallet twice with the same reference (an
  at-least-once event redelivery) only applies once; credit and debit don't
  collide on a shared reference value.
- **engagement**: a review must point at a real, completed lesson matching
  the tutor and student — not completed, wrong tutor, and a duplicate review
  for the same lesson are all rejected.
- **catalog**: full-text search finds a tutor by headline/description text
  and respects the price filter.

For a full live smoke test against every endpoint (not just these focused
cases), bring up the whole stack and run `python scripts/e2e.py`
(`DIRECT=1` to bypass the gateway and hit each department container by name).

## Roadmap

1. ✅ Monorepo, shared lib, gateway, full-stack compose.
2. ✅ All 22 original services implemented (now consolidated into 7 departments).
3. ✅ Event-driven choreography (now Redis Streams, at-least-once with ack-after-success).
4. ✅ Consolidation for a 4 GB / 13 GB host: 7 departments, one Postgres (schema
   per department), ElasticSearch/Kafka/MongoDB/RabbitMQ removed.
5. ✅ Fixed: review-manipulation via nullable `lesson_id`, missing calendar
   enforcement on booking, wallet double-credit race, un-authenticated
   internal service calls, dishonest "AI" labeling on template-only output.
6. ✅ pytest suite for the money/integrity paths above.
7. Remaining: CI/CD, k8s manifests (if ever needed beyond a single VPS),
   observability (Prometheus/Grafana/Loki), SMS/Telegram/Push notification
   channels, broader test coverage beyond the paths above.
