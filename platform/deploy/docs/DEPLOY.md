# Deploying EduBridge Academy to production

Target: `academy.edubridge.bond`, on the same VPS (`187.124.132.180`) that
already runs two sibling EduBridge projects (`edubridge.bond` — "Job", and
`university.edubridge.bond` — "University"). This doc assumes that
architecture, confirmed by reading the live server, not guessed:

- Ubuntu 22.04, **1 vCPU**, ~3.8 GB RAM (~2 GB genuinely free), ~12 GB free
  disk. This box was already hosting two full stacks before Academy — see
  "Resource risk" below.
- A single shared **nginx** container (`EduBridge_frontend`, part of the
  Job project, `/EduBridge_Job_1.0.0`) owns the host's `:80`/`:443` and
  TLS-terminates for every subdomain via `server_name` blocks baked into
  its image from `/EduBridge_Job_1.0.0/client/nginx.prod.conf`. It reverse
  proxies to each sibling project's containers by name over a shared
  **docker network**, `edubridge-net` (already exists on the host).
- **TLS is already fully automatic** and confirmed working (`certbot renew
  --dry-run` succeeds for both existing domains): a root crontab entry
  (`0 4 * * * certbot renew --quiet ...`) plus global pre/post renewal
  hooks at `/etc/letsencrypt/renewal-hooks/{pre,post}/` that stop/start the
  shared nginx container around each renewal (its authenticator is
  `standalone`, which needs port 80 briefly). Adding academy.edubridge.bond
  as a third domain to the same `/etc/letsencrypt/live/` slots it into this
  same automatic renewal — **no new script or cron needed for TLS.**
- **Backups** follow an established per-project convention: a script at
  `/usr/local/bin/backup-<project>-db.sh`, root crontab entry, `pg_dump`
  via `docker exec`, gzip, into the shared `/backups` directory, cleaned up
  with `find -mtime +N -delete`. Academy's version is
  `platform/deploy/scripts/backup-academy-db.sh` — see below.

Given all that, Academy's own stack needs **no TLS/ACME config of its own
at all** — it only needs to be reachable, by container name, from the
shared gateway.

## 1. Architecture this repo implements

```
                     shared nginx (Job project, EduBridge_frontend)
                     owns host :80/:443, terminates TLS for every domain
                              │
              ┌───────────────┼────────────────────┐
              ▼               ▼                     ▼
      edubridge.bond   university.edubridge.bond   academy.edubridge.bond
                                                      │
                                          proxy_pass http://academy_traefik:80
                                          (edubridge-net docker network)
                                                      │
                                              ┌───────┴────────┐
                                              │  academy_traefik │  (our own Traefik,
                                              │  academy-internal│   no host ports)
                                              └───────┬────────┘
                                     ┌─────────────────┼───────────────────┐
                                     ▼                 ▼                   ▼
                               frontend:3000    identity/engagement/...  postgres/redis
```

- `platform/docker-compose.yml` + `docker-compose.prod.yml`: the 6
  departments, Postgres, Redis, and our own Traefik. Only Traefik joins the
  shared `edubridge-net` network (as `academy_traefik`); everything else
  stays on the internal `academy-internal` network, unreachable from
  outside the docker host at all.
- `frontend/docker-compose.yml` + `docker-compose.prod.yml`: the Next.js
  app, deployed **independently** of the backend (redeploying one never
  rebuilds/restarts the other). Joins only `academy-internal`, so it's
  reachable at `http://frontend:3000` — by Traefik, never directly.
- Two GitHub Actions workflows (`.github/workflows/deploy-{backend,frontend}.yml`),
  path-filtered so a push only redeploys what actually changed.

## 2. One-time server setup

Run as `root` on the server.

**2.1 — Clone the repo**, matching the sibling projects' layout:

```bash
cd /
git clone https://github.com/abubakir2008/Academy_edubrdig.git EduBridge_Academy_1.0.0
cd EduBridge_Academy_1.0.0
```

**2.2 — Backend environment**:

```bash
cd platform
cp .env.production.example .env
# Fill in every CHANGE_ME — see the file's own comments for how to
# generate each secret. At minimum: JWT_PRIVATE_KEY/JWT_PUBLIC_KEY,
# INTERNAL_SECRET, POSTGRES_PASSWORD.
```

**2.3 — Frontend environment** (usually nothing to change):

```bash
cd ../frontend
cp .env.example .env
```

**2.4 — Bring up the backend first** (it creates the `academy-internal`
network the frontend attaches to):

```bash
cd ../platform
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

**2.5 — Bring up the frontend**:

```bash
cd ../frontend
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

**2.6 — Sanity check** from the host:

```bash
curl -fsS http://127.0.0.1:8091/api/auth/health
docker inspect --format='{{.State.Health.Status}}' frontend
```

**2.6a — Bootstrap the first admin account.** There's no self-registration
and no "promote to staff" endpoint — every account after this one is
created through the real `POST /auth/admin/users` API, logged in as this
one:

```bash
cd platform
./deploy/scripts/create-admin.sh you@example.com "Your Name" super_admin
```

Prints a one-time password — log in once at `academy.edubridge.bond/login`
and change it. Safe to re-run later for a second admin; add `--force` (via
`create_admin.py` directly) only if you actually mean to overwrite an
existing account's password.

**2.7 — Wire into the shared gateway** (touches the Job project's live
config — do this by hand, watching):

```bash
# Append platform/deploy/docker/nginx-gateway-snippet/academy.edubridge.bond.conf
# to the END of:
/EduBridge_Job_1.0.0/client/nginx.prod.conf

# Rebuild + restart just the shared gateway container:
cd /EduBridge_Job_1.0.0
docker compose -f docker-compose.prod.yml up -d --build frontend
```

**2.8 — Issue the certificate** (DNS for `academy.edubridge.bond` must
already resolve to this server — confirm with `dig +short
academy.edubridge.bond` before running this):

```bash
certbot certonly --standalone -d academy.edubridge.bond \
  --pre-hook "cd /EduBridge_Job_1.0.0 && docker compose -f docker-compose.prod.yml stop frontend" \
  --post-hook "cd /EduBridge_Job_1.0.0 && docker compose -f docker-compose.prod.yml start frontend"
```

This causes a few seconds of downtime for **all three** domains (the
shared gateway container briefly stops) — same as every renewal already
does. After this, `academy.edubridge.bond` is a third domain under the
existing automatic renewal; nothing further to configure for TLS, ever.

**2.9 — Install the backup script + cron**:

```bash
cp platform/deploy/scripts/backup-academy-db.sh /usr/local/bin/
cp platform/deploy/scripts/restore-academy-db.sh /usr/local/bin/
chmod +x /usr/local/bin/backup-academy-db.sh /usr/local/bin/restore-academy-db.sh

# Add to root's crontab (crontab -e) — 2:45 AM daily, staggered around the
# existing 2:00/3:00/4:00 AM jobs for the other two projects:
45 2 * * * /usr/local/bin/backup-academy-db.sh >> /var/log/backup-academy-db.log 2>&1
```

**2.10 — GitHub Actions secrets** (repo Settings → Secrets and variables →
Actions), so pushes to `master` (this repo's default branch) auto-deploy:

| Secret | Value |
|---|---|
| `SSH_HOST` | `187.124.132.180` |
| `SSH_USER` | `root` |
| `SSH_PASSWORD` | the server password |
| `SSH_PORT` | `22` (optional, defaults to 22) |

Rotate `SSH_PASSWORD` after setup if it was ever shared over a channel you
don't fully trust (e.g. plain chat) — same for the GitHub secret if you
ever rotate the server's actual password.

## 3. Redeploying

Just `git push` to `master`. `deploy-backend.yml` fires on `platform/**`
changes, `deploy-frontend.yml` on `frontend/**` changes — each rebuilds
and restarts only its own stack, waits for a health check, then prunes
old images.

## 4. Backups

- `backup-academy-db.sh`: daily `pg_dump` → gzip → `/backups/academy_<timestamp>.sql.gz`,
  keeps the last 7 days, deletes anything older than 8.
- `restore-academy-db.sh <file>`: replays a dump — asks for confirmation
  first, since it's destructive. **Test this at least once** against a
  disposable database before you actually need it; an unverified backup
  script is not a backup.
- Local disk only, matching what you asked for. If the VPS itself is ever
  lost (not just a bad deploy), the backups go with it — see "Gaps" below.

## 5. What's genuinely missing from this plan

Things worth deciding on, roughly in order of how much they'd hurt if
skipped:

1. **Resource contention.** This box now runs 3 full stacks on **1 vCPU**
   and ~3.8 GB RAM. Actual measured usage before Academy was light (~900 MB
   RSS combined across both existing projects' 8 containers), so there's
   probably enough RAM headroom — but CPU is the real risk: a single core
   shared three ways means a traffic spike on any one project can starve
   the others. Watch `docker stats` after go-live; if it's tight, an extra
   vCPU is the highest-leverage fix (cheaper than re-architecting).
2. **Off-site backups.** You asked for local-only, which is what's built —
   but it means server loss = data loss, not just downtime. Worth
   revisiting later even as something minimal (a weekly off-box copy).
3. **No CI gate before deploy.** Both workflows deploy straight from
   `git push` with no test run in between. `platform/tests/` (pytest) and
   `scripts/e2e.py` already exist — worth adding a `test` job that must
   pass before `deploy` runs, so a broken commit can't reach production
   automatically.
4. **Traefik dashboard** is off by default in production (no
   `--api.insecure` flag, no port published) — if you ever need it, tunnel
   in rather than exposing it: `ssh -L 18080:localhost:18080 root@187.124.132.180`
   then bring the stack up once with the override file.
5. **MinIO / object storage.** `docker-compose.yml`'s `minio` service is
   profile-gated (`full`) and, as built, has **no path from the public
   internet to it** in this shared-gateway topology (unlike the sibling
   projects, which each publish MinIO through their own proxy_pass). If
   avatars/certificates/course materials need to work, the shared
   gateway's `academy.edubridge.bond` block needs an additional
   `location /storage/` (or similar) proxying to `academy_minio:9000` —
   not included yet since it's unclear if `content`'s `storage` module is
   actually needed at launch.
5. **LiveKit / SMTP / Anthropic** are all optional-by-design (the app
   degrades to a clear error or a local fallback without them) — but
   decide now whether launch needs real lesson video calls and real email
   delivery, since those need real accounts/API keys only you can obtain
   (`.env.production.example` has the exact fields).
6. **No uptime/error alerting.** Nothing currently pages anyone if a
   department crashes or a backup silently fails. Even something minimal
   (a healthchecks.io ping wrapped around the backup cron, or an uptime
   monitor hitting `/api/auth/health`) would catch failures faster than
   "a user complains."
7. **No firewall configured in this pass** — `ufw`/security-group rules
   weren't touched. Worth confirming only 22/80/443 are reachable from the
   internet at the provider/VPS level.

## 6. Local development is unaffected

`docker compose up -d --build` in `platform/` and `frontend/` (in that
order — the network dependency) still works exactly as before;
`docker-compose.override.yml` in each is auto-loaded and restores the dev
port bindings (`:80`, `:18080` dashboard, `:5432`, `:6379`, `:9000`/`:9001`,
`:18025`, `:3000`, and each department's `:1800x` Swagger UI).
