# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1: builder — resolve and install runtime dependencies into a venv.
# Only pyproject.toml is copied here, so this (slow) layer stays cached until
# the dependency list actually changes. Source edits don't invalidate it.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

# Compilers live in this stage only; never copied into runtime.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /code
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# ---------------------------------------------------------------------------
# Stage 2: dev — builder + test/lint tooling + full source. Used by
# docker-compose (build.target: dev) so pytest and ruff exist locally.
# Never shipped to Fly.
# ---------------------------------------------------------------------------
FROM builder AS dev

RUN pip install ".[dev]"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/code

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# ---------------------------------------------------------------------------
# Stage 3: runtime — clean base + the prebuilt venv + only what runs in prod.
# Last stage, so `docker build` and `fly deploy` target it by default.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/code \
    PATH="/opt/venv/bin:$PATH"

COPY --from=builder /opt/venv /opt/venv

WORKDIR /code
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Non-root. UID is fixed so file ownership is reproducible across builds.
RUN useradd --create-home --uid 10001 appuser \
 && chown -R appuser:appuser /code
USER appuser

EXPOSE 8000

# Superseded by the [processes] block in fly.toml; kept so `docker run` works.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]