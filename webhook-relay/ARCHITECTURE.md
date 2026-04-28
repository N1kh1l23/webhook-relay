# Webhook Relay & Replay Service — Architecture

## What This System Does

A webhook debugging and replay tool. Users create a **source**, get a unique inbound URL, and any HTTP request sent to that URL is captured and stored. Users can inspect stored events and **replay** them to a destination URL. Failed deliveries are retried with exponential backoff, and permanently failed events land in a **dead-letter** state where they can be manually re-driven.

## Data Flow

```
External service (e.g. GitHub)
        │
        ▼
  POST /in/{source_token}
        │
        ├─ Verify HMAC signature (if configured)
        ├─ Check idempotency key (if provided)
        ├─ Check rate limit
        │
        ▼
  Store raw event in Postgres
  (headers, body, query params, metadata)
        │
        ▼
  Return 202 Accepted
        │
        ▼
  User inspects events via GET /sources/{id}/events
        │
        ▼
  User triggers replay: POST /events/{id}/replay
        │
        ▼
  Enqueue replay job in Redis
        │
        ▼
  Worker picks up job → POST to destination URL
        │
        ├─ 2xx → mark delivered, record DeliveryAttempt
        ├─ 5xx/429 → retry with exponential backoff + jitter
        └─ Max retries exceeded → move to dead-letter
```

## Postgres Schema

### sources
| Column           | Type         | Notes                              |
|------------------|--------------|------------------------------------|
| id               | UUID (PK)    | Auto-generated                     |
| name             | VARCHAR(255) | Human-readable label               |
| token            | VARCHAR(64)  | Unique, used in inbound URL path   |
| signing_secret   | VARCHAR(255) | Optional, for HMAC verification    |
| signing_provider | VARCHAR(50)  | e.g. "github", "stripe", or null   |
| created_at       | TIMESTAMPTZ  | Default now()                      |

### events
| Column       | Type         | Notes                                      |
|--------------|--------------|--------------------------------------------|
| id           | UUID (PK)    | Auto-generated                             |
| source_id    | UUID (FK)    | References sources.id                      |
| headers      | JSONB        | Raw request headers                        |
| body         | JSONB        | Raw request body                           |
| query_params | JSONB        | Raw query string params                    |
| status       | VARCHAR(20)  | pending / delivered / retrying / failed / dead_letter |
| received_at  | TIMESTAMPTZ  | Default now()                              |

### delivery_attempts
| Column          | Type         | Notes                             |
|-----------------|--------------|-----------------------------------|
| id              | UUID (PK)    | Auto-generated                    |
| event_id        | UUID (FK)    | References events.id              |
| destination_url | TEXT         | Where the replay was sent         |
| response_status | INTEGER      | HTTP status from destination      |
| response_body   | TEXT         | First 1000 chars of response      |
| duration_ms     | INTEGER      | Round-trip time                   |
| attempt_number  | INTEGER      | Which retry (1, 2, 3...)          |
| attempted_at    | TIMESTAMPTZ  | Default now()                     |

### idempotency_records (week 7)
| Column          | Type         | Notes                             |
|-----------------|--------------|-----------------------------------|
| key             | VARCHAR(255) | Unique per source                 |
| source_id       | UUID (FK)    | References sources.id             |
| response_status | INTEGER      | Cached response status            |
| response_body   | JSONB        | Cached response body              |
| created_at      | TIMESTAMPTZ  | Default now()                     |
| expires_at      | TIMESTAMPTZ  | 24 hours after creation           |

## Where Redis Fits

- **Worker queue**: Replay jobs are enqueued in Redis and consumed by an async worker process
- **Rate limiting** (week 8): Per-source request counters using INCR + EXPIRE

Redis is NOT the primary data store. Postgres is the system of record. Redis is used for transient state (queues, counters) where durability is not critical.

## Key Design Decisions

- **Why Postgres over SQLite**: Need concurrent access from API + worker processes; JSONB for flexible header/body storage; real constraints and transactions
- **Why Redis for the queue**: Lightweight, already in the stack for rate limiting, avoids adding Celery/RabbitMQ dependency for a simple job queue
- **Why HMAC verification is pluggable**: Different webhook providers (GitHub, Stripe) sign payloads differently. Base class with provider-specific implementations keeps the inbound handler clean
- **Why cursor-based pagination**: Events are append-heavy. Offset pagination breaks when new events arrive between pages. Cursor (keyset) pagination is stable
- **Retry policy**: Exponential backoff with jitter. 5xx and 429 are retryable; 4xx is not (a 404 won't fix itself). Max 5 attempts, then dead-letter
- **Idempotency**: Postgres INSERT ON CONFLICT on (key, source_id). Database-level uniqueness is simpler and more reliable than application-level locking
