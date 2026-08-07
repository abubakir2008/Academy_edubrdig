# EduBridge — Architecture

EduBridge is a Preply-style online tutoring marketplace built on FastAPI.
It runs as **7 department services**, each a merger of several of the
platform's original 22 microservices, sized to fit a 4 GB / 13 GB VPS. This
document is the high-level map; see [SERVICES.md](SERVICES.md) for the
per-route index.

## 1. Big picture

```
                        ┌──────────────┐
   mobile / web  ─────▶ │   Traefik    │   http://localhost/api/<prefix>/...
                        │  (gateway)   │   strips /api, routes by path prefix
                        └──────┬───────┘
   ┌──────────┬─────────┼──────────┬────────────┬─────────┬────────────┐
   ▼          ▼         ▼          ▼            ▼         ▼            ▼
identity   catalog  scheduling  finance     engagement  content   backoffice
   │          │         │          │            │         │            │
   └──────────┴───── one Postgres (schema per department) ┴────────────┘
                              │
                    one Redis (Streams event bus,
                     tokens, rate-limit, realtime)
```

- **Gateway:** Traefik. One router per original route prefix (still 22 of
  them — `auth`, `tutors`, `booking`, ...), each pointing at the department
  container that now serves it. `PathPrefix(/api/<prefix>)` + `StripPrefix(/api)`.
  A department therefore still namespaces its routes under each of its
  original prefixes (e.g. the `identity` container serves both `/auth/...`
  and `/users/...`).
- **Departments:** 7 FastAPI apps, each its own container, its own OpenAPI
  docs at `/docs`, all built from the **same image** (see `Dockerfile` —
  `$DEPARTMENT` selects which department's code runs).
- **Event bus:** Redis Streams. Departments publish domain events and consume
  the ones they care about — no synchronous department-to-department calls
  for anything that can be eventual.

## 2. Why departments, not 22 services

The 22-service layout needed ElasticSearch + Kafka + MongoDB + RabbitMQ + 22
uvicorn containers — about 5.4 GB of RAM to start, more than a 4 GB host has.
Consolidating containers alone wouldn't have fixed that; the infrastructure
that only existed to serve one query each had to go too:

- **ElasticSearch → Postgres full-text.** `catalog`'s `search` module now
  queries the `tutors` table directly via a generated `tsvector` column
  (`catalog/app/modules/tutors/models/tutor.py::search_vector`). No separate
  index, no reindex step, no replication lag.
- **Kafka → Redis Streams.** `shared/edubridge_shared/events.py`. Same
  consumer-group fan-out semantics, a fraction of the memory.
- **MongoDB → Postgres.** `chat`, `notifications`, `support` kept their
  document shapes but moved into their department's Postgres schema.
- **RabbitMQ → removed.** It was provisioned in the original compose file but
  no service ever imported it.
- **15 Postgres databases → 1 database, 7 schemas.** Each department owns one
  schema (`identity`, `catalog`, `scheduling`, `finance`, `engagement`,
  `content`, `backoffice`) instead of its modules each owning a database.

Departments group services by what they operate on together, so most of what
used to be a cross-service HTTP call is now an in-process function call:
Booking checking Calendar availability, Search reading the Tutors table,
Lessons reacting to a booking confirmation — same department, no network hop.
A few genuinely cross-department calls remain (e.g. Reviews verifying a
lesson with Scheduling) — these forward the caller's own JWT rather than a
shared service credential, so the target's normal per-user authorization
still applies.

## 3. Datastores

| Store | Used by |
|---|---|
| PostgreSQL (one DB, 7 schemas) | every department |
| Redis | tokens (db 0), video rooms (db 1), rate-limit (db 2), realtime pub/sub (db 3), event bus (db 4) |
| MinIO | `content` department's `storage` module |

One `alembic upgrade head` runs per department (against its own schema) from
`entrypoint.sh` before that department serves traffic — 7 migration runs on
boot, not 22.

## 4. Identity & authentication

- **Identity department** (`auth` module) issues JWT **access** (short-lived)
  and **refresh** (long-lived, rotated, revocable via Redis) tokens.
- The token `sub` claim is the user id; the same id is the primary key of the
  user's profile in every department's tables (no cross-schema foreign keys —
  schemas are isolated on purpose, same as separate databases used to be).
- Every other department only **verifies** tokens, using the shared secret
  via `edubridge_shared.fastapi_auth.build_auth_dependencies`. No department
  calls identity at request time.
- OAuth (Google / Apple): native mobile flow — the app performs sign-in and
  sends the `id_token`, which identity verifies against the provider's JWKS.

### Roles

`student`, `tutor`, `admin`, `super_admin`, `moderator`, `support_manager`,
`finance_manager`, `content_manager`. Only `student`/`tutor` are self-assignable
at registration; staff roles are assigned by an admin. Role checks use
`require_roles(...)`.

## 5. Event-driven choreography

Producers publish; consumers react autonomously (no frontend orchestration).
Each department consumes with its **own consumer group**, so an event fans
out to every interested department.

| Event | Producer | Consumers → effect |
|---|---|---|
| `payment.succeeded` | finance (payments) | finance (wallet, credits tutor — idempotent), engagement (notifications), backoffice (analytics) |
| `payment.refunded` | finance (payments) | engagement (notifications), backoffice (analytics) |
| `booking.created` | scheduling (booking) | engagement (notifications), backoffice (analytics) |
| `booking.confirmed` | scheduling (booking) | scheduling (lessons, auto-creates the lesson — idempotent), engagement (notifications), backoffice (analytics) |
| `booking.cancelled` | scheduling (booking) | engagement (notifications), backoffice (analytics) |
| `lesson.completed` | scheduling (lessons) | engagement (notifications — ask for review), backoffice (analytics) |
| `review.created` | engagement (reviews) | catalog (tutors, updates rating), engagement (notifications), backoffice (analytics) |
| `tutor.verified` | backoffice (moderation) | catalog (tutors, sets is_verified), engagement (notifications), backoffice (analytics) |

**Reliability characteristics:**
- Publishing is *best-effort*: a down Redis logs a warning and never breaks
  the HTTP request that triggered the event.
- Delivery is *at-least-once*, but a message is only acknowledged after every
  handler for it succeeds — not before, the way naive auto-commit consumers
  do it. A crash mid-handler leaves the message pending; it's picked back up
  by `XAUTOCLAIM` after an idle timeout, by this or another consumer in the
  same group.
- **Idempotency is enforced at two levels.** The bus itself marks each event
  id as seen (`SET NX`) so an ordinary redelivery is a no-op; and the two
  handlers that move money or create records enforce it again at the
  database level — wallet crediting via a unique constraint on
  `(reference, type)`, lesson auto-creation via `get_by_booking`. This
  closes the "double-credit on redelivery" gap the platform had before.
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
- `clients.py` — `ServiceClient` for the few remaining cross-department
  calls (attaches `X-Internal-Secret`); `require_internal` guards any
  endpoint meant to be internal-only.
- `app_factory.py` — builds a consistent FastAPI app: logging, one
  `/<prefix>/health` per route prefix the department serves, lifespan hooks.
- `logging.py` — JSON logging; `schemas.py` — common response models;
  `realtime.py` — Redis pub/sub for WebSocket fan-out (chat, notifications).

## 7. Request routing recap

```
client → /api/tutors?language=english         (Traefik: strip /api)
       → catalog container: GET /tutors?...   (router prefix /tutors,
                                                 module modules/tutors)
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

`tests/` (pytest) covers the money- and integrity-sensitive paths — see
`README.md`'s Testing section for what's covered and `make test` to run it.

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
- Test coverage beyond the paths in `tests/` — the suite is deliberately
  focused on what was actually broken (calendar enforcement, wallet
  idempotency, review verification, search) rather than exhaustive.
