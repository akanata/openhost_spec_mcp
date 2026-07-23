# health-mcp

A read-only [MCP](https://modelcontextprotocol.io) server that exposes your OpenHost
[health data](https://github.com/imbue-openhost/health-data-service-spec) (sleep,
workouts, heart rate, and any other metrics your connected providers report — Oura,
Apple Watch, etc.) to AI agents, over the network, as an OpenHost app.

It's a thin read-only layer: every tool wraps a `GET`-only method on the upstream
`HealthDataClient`, merged across every connected provider. There is no write path in
this server, in the client library it wraps, or in the manifest — an agent talking to
it cannot alter your health data even in principle.

## Tools

| Tool | Description |
|---|---|
| `list_metrics` | Every metric available across all connected providers |
| `list_providers` | Which data sources are connected (e.g. Oura, Apple Watch) and their status |
| `get_time_series` | Samples for one metric (e.g. `heart_rate`) over a time range |
| `get_sleep_sessions` | Sleep sessions over a time range |
| `get_workouts` | Workout summaries, optionally filtered by type/time range |
| `get_workout` | Full detail (heart-rate trace, GPS route) for one workout |

## Deploying

From the OpenHost dashboard, "Deploy New App" with this repo's URL — or via the `oh`
CLI:

```bash
oh app deploy https://github.com/<you>/openhost_spec_mcp --name health-mcp --wait
```

This installs `health-mcp` as a consumer of the `health-data-service-spec` service (see
`openhost.toml`); make sure a provider of that service (an app that actually syncs data
from Oura, Apple Health, etc.) is already installed in your compute space, or the tools
will have nothing to return.

## Connecting an AI agent

The MCP endpoint is `https://health-mcp.<your-zone-domain>/mcp` (streamable-HTTP
transport). It's owner-only: `/mcp` bypasses the router's default login-cookie gate
(since a non-browser MCP client can't present one) but the app itself rejects any
request that isn't authenticated as the compute space owner.

To connect, mint an owner-scoped API token and hand it to your MCP client as a bearer
token:

```bash
oh tokens create --name "health-mcp client" --expiry-hours 720
```

Then add it to your client's MCP config, e.g. for Claude Code:

```bash
claude mcp add --transport http health https://health-mcp.<your-zone-domain>/mcp \
  --header "Authorization: Bearer <token from oh tokens create>"
```

## Local development

Requires [`uv`](https://docs.astral.sh/uv/) and [`just`](https://github.com/casey/just).

```bash
just setup   # install deps + pre-commit hooks
just run     # serve on http://localhost:8080 (auto-reload)
just test    # run the test suite
just check   # ruff + mypy, same checks as pre-commit
just build   # build the container image
```

`just test` runs the fast, in-process test suite (no container, no OpenHost router).
The suite also includes `tests/conftest.py`'s `stack` fixture, which builds and runs
the real Dockerfile under `podman`, fronted by the real OpenHost router — that part
requires `podman` on the host and isn't exercised by the fast suite; use it to validate
the auth/routing wiring against the genuine router before deploying.

Outside a real OpenHost container, tools that actually fetch data will fail (no
`OPENHOST_ROUTER_URL` to call) — set `OPENHOST_ROUTER_URL` and `OPENHOST_APP_TOKEN`
yourself (e.g. pointed at a local `openhost up` instance) to exercise the full path.
