from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import attrs
from health_data_service import HealthDataClient
from mcp.server.fastmcp import Context
from mcp.server.fastmcp import FastMCP
from mcp.server.session import ServerSession


@attrs.define(frozen=True)
class AppContext:
    client: HealthDataClient


# Shorthand for the Context type every tool function receives: a request-scoped
# handle whose lifespan_context is our AppContext (see app_lifespan below).
type AppCtx = Context[ServerSession, AppContext, Any]


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    # With stateless_http=True (below), the SDK re-enters this lifespan fresh for
    # every single request rather than once per container lifetime — so this
    # constructs a new HealthDataClient (and its underlying httpx connection) per MCP
    # call. Fine here: every tool is a cheap, infrequent read, not a hot path.
    async with HealthDataClient() as client:
        yield AppContext(client=client)


# host="0.0.0.0" disables the SDK's default DNS-rebinding protection (which only
# allowlists 127.0.0.1/localhost and would reject every request proxied in by the
# real OpenHost router); our own owner-only guard in app.py is the real boundary.
# stateless_http=True fits this server well: every tool is a single-shot read with
# no elicitation or long-lived streaming, so there's no session state worth keeping
# across a container restart.
mcp = FastMCP("health-mcp", lifespan=app_lifespan, host="0.0.0.0", stateless_http=True)

from server import mcp_tools  # noqa: E402, F401  # registers tools via decorator side effects
