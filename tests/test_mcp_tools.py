from datetime import UTC
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from health_data_service import Calories
from health_data_service import Duration
from health_data_service import HeartRate
from health_data_service import MetricKind
from health_data_service import MetricType
from health_data_service import RunningWorkout
from health_data_service import Sample
from health_data_service import SleepSession
from health_data_service import TimeSeries

from server.mcp_server import AppContext
from server.mcp_tools import _parse
from server.mcp_tools import get_sleep_sessions
from server.mcp_tools import get_time_series
from server.mcp_tools import get_workout
from server.mcp_tools import get_workouts
from server.mcp_tools import list_metrics
from server.mcp_tools import list_providers


def _ctx(**client_methods: Any) -> Any:
    client = SimpleNamespace(**client_methods)
    return SimpleNamespace(request_context=SimpleNamespace(lifespan_context=AppContext(client=client)))


def test_parse_handles_iso8601_and_none() -> None:
    assert _parse(None) is None
    assert _parse("2024-01-01T00:00:00Z") == datetime(2024, 1, 1, tzinfo=UTC)


async def test_list_metrics_unstructures_merged_result() -> None:
    metrics = [MetricType(metric_id="heart_rate", display_name="Heart Rate", kind=MetricKind.TIME_SERIES, unit="bpm")]
    ctx = _ctx(list_metrics_merged=AsyncMock(return_value=metrics))
    result = await list_metrics(ctx)
    assert result == [{"metric_id": "heart_rate", "display_name": "Heart Rate", "kind": "time_series", "unit": "bpm"}]


async def test_list_providers_passes_through_raw_provider_list() -> None:
    providers = [{"app_id": "abc123", "app_name": "oura", "status": "running"}]
    ctx = _ctx(discover_providers=AsyncMock(return_value=providers))
    result = await list_providers(ctx)
    assert result == providers


async def test_get_time_series_parses_bounds_and_forwards_request() -> None:
    ts = TimeSeries(
        metric_id="heart_rate",
        display_name="Heart Rate",
        unit="bpm",
        samples=[Sample(timestamp=datetime(2024, 1, 1, tzinfo=UTC), value=72.0)],
        source="oura",
    )
    mock_method = AsyncMock(return_value=ts)
    ctx = _ctx(get_time_series_merged=mock_method)

    result = await get_time_series("heart_rate", ctx, start="2024-01-01T00:00:00Z", end=None, limit=5)

    req = mock_method.call_args.args[0]
    assert req.metric == "heart_rate"
    assert req.start == datetime(2024, 1, 1, tzinfo=UTC)
    assert req.end is None
    assert req.limit == 5
    assert result["metric_id"] == "heart_rate"
    assert result["samples"] == [{"timestamp": "2024-01-01T00:00:00+00:00", "value": 72.0}]


async def test_get_sleep_sessions_unstructures_each_session() -> None:
    session = SleepSession(
        start=datetime(2024, 1, 1, tzinfo=UTC),
        end=datetime(2024, 1, 1, 8, tzinfo=UTC),
        id="sess1",
        heart_rate=HeartRate(samples=[Sample(timestamp=datetime(2024, 1, 1, tzinfo=UTC), value=55.0)], source="oura"),
    )
    ctx = _ctx(get_sleep_sessions_merged=AsyncMock(return_value=[session]))

    result = await get_sleep_sessions(ctx, limit=1)

    assert len(result) == 1
    assert result[0]["id"] == "sess1"
    assert result[0]["heart_rate"]["samples"][0]["value"] == 55.0


async def test_get_workouts_unstructures_subclass_specific_fields() -> None:
    workout = RunningWorkout(
        start=datetime(2024, 1, 1, tzinfo=UTC),
        end=datetime(2024, 1, 1, 1, tzinfo=UTC),
        id="w1",
        duration=Duration(value=60.0, source="oura"),
        calories=Calories(value=500.0, source="oura"),
        source="oura",
    )
    mock_method = AsyncMock(return_value=[workout])
    ctx = _ctx(get_workouts_merged=mock_method)

    result = await get_workouts(ctx, workout_type="running")

    req = mock_method.call_args.args[0]
    assert req.workout_type == "running"
    # The whole point of unstructuring rather than returning attrs objects: subclass-only
    # fields (workout_type here) must survive, not just Workout's own base fields.
    assert result[0]["workout_type"] == "running"
    assert result[0]["duration"]["value"] == 60.0


async def test_get_workout_returns_none_when_not_found() -> None:
    ctx = _ctx(get_workout_merged=AsyncMock(return_value=None))
    assert await get_workout("missing", ctx) is None
