import os
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


class KillSwitchMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        enabled = os.getenv("KILL_SWITCH_ENABLED", "false").lower() == "true"

        if enabled:
            return JSONResponse(
                {"detail": "Service temporarily disabled (kill switch active)"},
                status_code=503,
            )

        return await call_next(request)