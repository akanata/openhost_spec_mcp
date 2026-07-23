from collections.abc import Iterator

import pytest
from litestar.testing import TestClient
from openhost_test_harness import OpenhostStack

from server.app import app


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """In-process ASGI test client for the Litestar app (no container, no podman).

    Session-scoped and shared across tests: the mcp SDK's StreamableHTTPSessionManager
    is a one-shot object (its .run() may only be entered once per instance, matching one
    real container's lifetime), so each test must NOT open its own TestClient — that
    would enter/exit the app lifespan, and the session manager, more than once.
    """
    with TestClient(app=app) as c:
        yield c


@pytest.fixture(scope="session")
def stack() -> Iterator[OpenhostStack]:
    """Build the app's Dockerfile, run it under podman per openhost.toml, and
    front it with the real OpenHost router. Requires podman on the host.

    OpenhostStack() finds openhost.toml by walking up from the cwd, so no app_dir
    is needed as long as tests run from within the app tree.

    - stack.url                   — through the router; requires owner auth
    - stack.owner_session         — a requests.Session authenticated as the zone owner
    - stack.app_url                — direct to the container (control your own headers; eg the health probe)
    """
    with OpenhostStack() as s:
        yield s
