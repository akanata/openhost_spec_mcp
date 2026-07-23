import json

import pytest
from litestar.testing import TestClient

MCP_HEADERS = {
    "accept": "application/json, text/event-stream",
    "content-type": "application/json",
}

INITIALIZE_BODY = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0"},
    },
}


@pytest.fixture(autouse=True)
def _health_service_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # The MCP lifespan constructs a HealthDataClient() on every request (see
    # mcp_server.py: stateless_http=True re-enters the tool-level lifespan per call),
    # which reads these at construction time. The client only touches the network
    # lazily, so a placeholder URL is enough to let the lifespan itself succeed.
    monkeypatch.setenv("OPENHOST_ROUTER_URL", "http://127.0.0.1:1")
    monkeypatch.setenv("OPENHOST_APP_TOKEN", "test-token")


def _sse_json(response_text: str) -> dict:
    return json.loads(response_text.split("data: ", 1)[1])


def test_mcp_rejects_request_without_owner_header(client: TestClient) -> None:
    response = client.post("/mcp", headers=MCP_HEADERS, json=INITIALIZE_BODY)
    assert response.status_code == 401


def test_mcp_rejects_request_with_owner_header_false(client: TestClient) -> None:
    response = client.post("/mcp", headers={**MCP_HEADERS, "x-openhost-is-owner": "false"}, json=INITIALIZE_BODY)
    assert response.status_code == 401


def test_mcp_initialize_succeeds_for_owner(client: TestClient) -> None:
    response = client.post("/mcp", headers={**MCP_HEADERS, "x-openhost-is-owner": "true"}, json=INITIALIZE_BODY)
    assert response.status_code == 200
    body = _sse_json(response.text)
    assert body["result"]["serverInfo"]["name"] == "health-mcp"


def test_mcp_tools_list_exposes_read_only_tools_without_leaking_context_param(client: TestClient) -> None:
    response = client.post(
        "/mcp",
        headers={**MCP_HEADERS, "x-openhost-is-owner": "true"},
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    )
    tools = {t["name"]: t for t in _sse_json(response.text)["result"]["tools"]}
    assert set(tools) == {
        "list_metrics",
        "list_providers",
        "get_time_series",
        "get_sleep_sessions",
        "get_workouts",
        "get_workout",
    }
    for tool in tools.values():
        assert "ctx" not in tool["inputSchema"].get("properties", {})
