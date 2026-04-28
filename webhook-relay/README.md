# Webhook Relay & Replay Service

Capture, inspect, and replay webhooks. Built with FastAPI, Postgres, and Redis.

> 🚧 Under active development — see [ARCHITECTURE.md](ARCHITECTURE.md) for the full design.

## Quick Start

```bash
docker-compose up --build
```

API available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

## Run Tests

```bash
pytest tests/ -v
```
