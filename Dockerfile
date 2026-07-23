FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# health-data-service is a git dependency (see pyproject.toml); uv shells out to a
# real git binary to fetch it, which python:3.12-slim doesn't ship by default.
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (source is copied first so the project itself
# builds during `uv sync`).
COPY pyproject.toml uv.lock ./
COPY src/ src/
RUN uv sync --frozen --no-dev

EXPOSE 8080

CMD ["uv", "run", "--frozen", "--no-dev", "hypercorn", "server.app:app", "--bind", "0.0.0.0:8080"]
