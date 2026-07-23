default: test

# Install dependencies, pre-commit hooks.
setup:
    uv sync
    uv run pre-commit install

# Run the app locally on http://localhost:8080 (auto-reloads on change).
run:
    uv run hypercorn server.app:app --bind 0.0.0.0:8080 --reload

# Run the test suite.
test:
    uv run pytest -x

# Lint, format, and typecheck (same checks as the pre-commit hooks).
check:
    uv run ruff check --fix .
    uv run ruff format .
    uv run mypy

# Build the container image.
build:
    docker build -t health-mcp .
