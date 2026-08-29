# Webhook Relay & Replay Service

Capture incoming webhooks, inspect them, and replay them to any destination — with a full audit trail of every delivery attempt.

**Live:** https://nikhil-webhook-relay.fly.dev · **API docs:** https://nikhil-webhook-relay.fly.dev/docs

## What it does

Create a *source* and you get a unique inbound URL. Any HTTP request sent to that URL is captured whole — headers, body, query params — and stored. You can then replay any captured event to a destination of your choice and see exactly what happened: status code, response body, round-trip time.

The use case is webhook debugging. A provider fires a webhook at your staging environment, it fails, and the provider won't resend it. Point the provider here instead, and you can replay that exact payload against your service as many times as you need.

## Architecture

The API writes to Postgres directly. Redis carries the job, and the worker takes the job off the queue, sends it to the destination, and then writes a `DeliveryAttempt` row according to what took place.

```
  POST /in/{token}                    POST /events/{id}/replay
         │                                      │
         ▼                                      ▼
   ┌───────────┐                          ┌───────────┐
   │  FastAPI  │──── event row ─────────▶ │ Postgres  │
   └───────────┘                          └───────────┘
         │                                      ▲
         │ enqueue job                          │ attempt row
         ▼                                      │
   ┌───────────┐                          ┌───────────┐
   │   Redis   │──── job ───────────────▶ │ arq worker│───▶ destination
   └───────────┘                          └───────────┘
```

Delivery is slow and can fail, so it doesn't run in the request path. `/replay` returns `202` with a job id immediately; the client polls `/events/{id}/attempts` for the outcome.

Both the web process and the worker run the same image with different commands — two Fly process groups, one Dockerfile.

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/sources` | Create a source, returns its inbound token |
| `GET` | `/sources/{id}/events` | Events captured by this source, newest first |
| `POST` | `/in/{token}` | Inbound capture. Returns `202` |
| `POST` | `/events/{id}/replay` | Queue a replay. Returns `202` and a job id |
| `GET` | `/events/{id}/attempts` | Delivery history for an event |
| `GET` | `/health` | Per-dependency status. Always `200` |

## Try it

`demo.sh` runs the whole flow against the live service — creates a source, sends a webhook, replays it to httpbin, and polls until the worker records the delivery. Requires `jq`.

```bash
./demo.sh                              # against the live URL
./demo.sh http://localhost:8000        # against a local stack
```

## Run locally

```bash
docker compose up --build
docker compose exec api alembic upgrade head
```

API on `http://localhost:8000`. Four services: `api`, `worker`, `db`, `redis`.

Tests:

```bash
docker compose exec api pytest tests/ -v
docker compose exec api ruff check .
```

The Dockerfile has three stages. Compose builds the `dev` target, which includes pytest and ruff; the default target is `runtime`, which ships only the production venv and runs non-root.

## Stack

FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL · Alembic · Redis · arq · Docker · Fly.io

## Deployment notes

Deployed to Fly.io as a single app with two process groups. Migrations run via `release_command` in `fly.toml`, in a temporary machine before the release goes live — a failed migration aborts the deploy rather than leaving a broken release running.

A few things that took some working out:

- **`DATABASE_URL` needs normalizing.** `fly postgres attach` sets `postgres://…?sslmode=disable`. SQLAlchemy 2.0 rejects the `postgres` scheme, the async engine needs `+asyncpg`, and asyncpg raises on `sslmode` as a connection parameter. A field validator in `app/config.py` rewrites all three and is idempotent, so the local default passes through untouched.
- **`.internal`, not `.flycast`.** `attach` writes a `.flycast` host, which routes through Fly's proxy. That's fine for the short-lived connection Alembic opens, but it broke the long-lived pooled connections the async engine holds — migrations succeeded while `/health` reported Postgres down. The secret is set manually to `.internal`; re-running `attach` will overwrite it.
- **`poll_delay = 2` on the worker.** Upstash bills per command and arq polls continuously, so the 0.5s default costs roughly four times as much for an idle worker.
- **`/health` always returns 200.** It reports each dependency separately and an overall `ok`/`degraded`. Fly's check treats it as liveness only, so a transient Postgres blip doesn't get the machine restarted.

## CI

GitHub Actions on every push: ruff, `alembic upgrade head` against a Postgres service container, and pytest. A parallel job builds the runtime image target.