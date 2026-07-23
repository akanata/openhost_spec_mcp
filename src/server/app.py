from typing import Any
from typing import cast

from litestar import Litestar
from litestar import asgi
from litestar import get
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.handlers.base import BaseRouteHandler
from litestar.types import Receive
from litestar.types import Scope
from litestar.types import Send

from server.mcp_server import mcp

# Side effect: constructs mcp.session_manager (created lazily, only by this call).
# We bypass this Starlette app's own internal routing (Litestar's mount rewrites
# scope["path"] to the remainder after "/mcp", which wouldn't match the sub-app's
# own route registered at streamable_http_path) and drive session_manager.handle_request
# directly instead.
mcp.streamable_http_app()


def mcp_owner_guard(connection: ASGIConnection[Any, Any, Any, Any], _: BaseRouteHandler) -> None:
    if connection.headers.get("x-openhost-is-owner") != "true":
        raise NotAuthorizedException()


@asgi("/mcp", is_mount=True, copy_scope=True, guards=[mcp_owner_guard])
async def mcp_endpoint(scope: Scope, receive: Receive, send: Send) -> None:
    # Litestar and the mcp SDK each define their own nominal types over the same
    # underlying ASGI scope/receive/send protocol; cast across that boundary.
    await mcp.session_manager.handle_request(cast(Any, scope), cast(Any, receive), cast(Any, send))


@get("/health", sync_to_thread=False)
def health() -> dict[str, str]:
    return {"status": "ok"}


app = Litestar(
    route_handlers=[health, mcp_endpoint],
    # A callable, not a pre-built context manager: `.run()` returns a single-use
    # async context manager, so it must be constructed fresh on each lifespan entry
    # (Litestar calls `manager(self)` itself) rather than shared as one instance.
    lifespan=[lambda _: mcp.session_manager.run()],
)
