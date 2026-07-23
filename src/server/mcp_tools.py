from datetime import datetime
from typing import Any
from typing import cast

from health_data_service import HealthDataClient
from health_data_service import SleepSessionsRequest
from health_data_service import TimeSeriesRequest
from health_data_service import WorkoutsRequest
from mcp.server.fastmcp import Context

from server.mcp_server import AppContext
from server.mcp_server import AppCtx
from server.mcp_server import mcp
from server.serialization import unstructure

# The SDK's context auto-detection (mcp.server.fastmcp.utilities.context_injection.
# find_context_parameter) only recognizes an unparametrized `Context` annotation on a
# @mcp.tool()-decorated function; a subscripted alias like AppCtx isn't matched, so the
# parameter would end up in the tool's client-facing input schema instead of being
# injected. Confirmed by reading actual tools/list output. Bare Context fails strict
# mypy's disallow_any_generics, hence the ignores below; AppCtx (which mypy checks in
# full) is used everywhere else, i.e. in _client().


def _parse(timestamp: str | None) -> datetime | None:
    return datetime.fromisoformat(timestamp) if timestamp is not None else None


def _client(ctx: AppCtx) -> HealthDataClient:
    app_ctx: AppContext = ctx.request_context.lifespan_context
    return app_ctx.client


@mcp.tool()
async def list_metrics(ctx: Context) -> list[dict[str, Any]]:  # type: ignore[type-arg]
    """List every metric available across all connected health data providers."""
    metrics = await _client(ctx).list_metrics_merged()
    return [unstructure(m) for m in metrics]


@mcp.tool()
async def list_providers(ctx: Context) -> list[dict[str, Any]]:  # type: ignore[type-arg]
    """List the connected health data source apps (e.g. Oura, Apple Watch) and their status."""
    return await _client(ctx).discover_providers()


@mcp.tool()
async def get_time_series(
    metric: str,
    ctx: Context,  # type: ignore[type-arg]
    start: str | None = None,
    end: str | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Get samples for one metric (e.g. "heart_rate") merged across all providers.

    start/end are ISO-8601 timestamps (e.g. "2024-01-01T00:00:00Z"); omit either to leave that
    bound open. limit caps the number of samples returned.
    """
    req = TimeSeriesRequest(metric=metric, start=_parse(start), end=_parse(end), limit=limit)
    ts = await _client(ctx).get_time_series_merged(req)
    return cast(dict[str, Any], unstructure(ts))


@mcp.tool()
async def get_sleep_sessions(
    ctx: Context,  # type: ignore[type-arg]
    start: str | None = None,
    end: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """List sleep sessions merged across all providers, most recent first.

    start/end are ISO-8601 timestamps; omit either to leave that bound open.
    """
    req = SleepSessionsRequest(start=_parse(start), end=_parse(end), limit=limit)
    sessions = await _client(ctx).get_sleep_sessions_merged(req)
    return [unstructure(s) for s in sessions]


@mcp.tool()
async def get_workouts(
    ctx: Context,  # type: ignore[type-arg]
    workout_type: str | None = None,
    start: str | None = None,
    end: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """List workout summaries merged across all providers, most recent first.

    workout_type filters to one activity (e.g. "running", "cycling"); omit for all types.
    Summaries carry scalar metrics only (no per-sample time series or GPS route) — use
    get_workout for full detail on a specific workout.
    """
    req = WorkoutsRequest(workout_type=workout_type, start=_parse(start), end=_parse(end), limit=limit)
    workouts = await _client(ctx).get_workouts_merged(req)
    return [unstructure(w) for w in workouts]


@mcp.tool()
async def get_workout(workout_id: str, ctx: Context) -> dict[str, Any] | None:  # type: ignore[type-arg]
    """Get full detail (heart-rate trace, GPS route) for one workout by id. Returns null if not found."""
    workout = await _client(ctx).get_workout_merged(workout_id)
    return unstructure(workout) if workout is not None else None
