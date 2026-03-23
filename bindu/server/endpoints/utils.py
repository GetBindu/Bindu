"""Common request utilities for endpoint handlers."""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Tuple, Type, get_args

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.common.protocol.types import InternalError
from bindu.utils.logging import get_logger
from bindu.settings import app_settings

logger = get_logger("bindu.server.endpoints.utils")


def get_client_ip(request: Request) -> str:
    """Extract client IP address from request.

    Args:
        request: Starlette request object

    Returns:
        Client IP address or "unknown" if not available
    """
    return request.client.host if request.client else "unknown"


def extract_error_fields(err_alias: Type[Any]) -> Tuple[int, str]:
    """Extract error code and message from JSONRPCError type alias.

    Given a JSONRPCError[Literal[code], Literal[message]] typing alias,
    return (code, message) as runtime values.
    """
    code_lit, msg_lit = get_args(err_alias)
    (code,) = get_args(code_lit)
    (msg,) = get_args(msg_lit)
    return int(code), str(msg)


def jsonrpc_error(
    code: int,
    message: str,
    data: str | None = None,
    request_id: Any = None,
    status: int = 400,
) -> JSONResponse:
    """Create a JSON-RPC error response.

    Args:
        code: JSON-RPC error code
        message: Error message
        data: Optional additional error data
        request_id: Optional JSON-RPC request ID
        status: HTTP status code (default: 400)

    Returns:
        JSONResponse with JSON-RPC error format
    """
    error_dict: dict[str, Any] = {"code": code, "message": message}
    if data:
        error_dict["data"] = data

    return JSONResponse(
        content={
            "jsonrpc": "2.0",
            "error": error_dict,
            "id": str(request_id) if request_id is not None else None,
        },
        status_code=status,
    )


def handle_endpoint_errors(endpoint_name: str) -> Callable:
    """Decorate endpoint to handle common errors.

    Args:
        endpoint_name: Name of the endpoint for logging (e.g., "agent card", "skills list")

    Returns:
        Decorated endpoint function with error handling

    Example:
        @handle_endpoint_errors("agent card")
        async def agent_card_endpoint(app, request):
            # Your endpoint logic here
            return response
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Response:
            # Extract request from args/kwargs
            request: Request | None = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request and "request" in kwargs:
                request = kwargs["request"]

            client_ip = get_client_ip(request) if request else "unknown"

            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Error serving {endpoint_name} to {client_ip}: {e}", exc_info=True
                )
                code, message = extract_error_fields(InternalError)
                return jsonrpc_error(code, message, str(e), status=500)

        return wrapper

    return decorator


def validate_manifest(
    app: Any,
    client_ip: str = "unknown",
    use_jsonrpc: bool = False,
    error_type: Type[Any] = InternalError,
) -> JSONResponse | None:
    """Validate manifest exists, return error response if not.

    Args:
        app: BinduApplication instance
        client_ip: Client IP for logging
        use_jsonrpc: Whether to use JSON-RPC error format
        error_type: Error type to use for JSON-RPC errors

    Returns:
        None if manifest exists, error response otherwise
    """
    if app.manifest is not None:
        return None

    if use_jsonrpc:
        logger.warning(f"Manifest not configured (requested by {client_ip})")
        code, message = extract_error_fields(error_type)
        return jsonrpc_error(code, message, "Agent manifest not configured", status=500)
    else:
        return JSONResponse(
            content={"error": "Agent manifest not configured"}, status_code=500
        )


def get_agent_did(app: Any) -> str | None:
    """Extract agent DID from manifest.

    Args:
        app: BinduApplication instance

    Returns:
        Agent DID if available, None otherwise
    """
    if (
        app.manifest
        and hasattr(app.manifest, "did_extension")
        and app.manifest.did_extension
    ):
        return app.manifest.did_extension.did
    return None


def get_runtime_status(app: Any) -> dict:
    """Get runtime status information.

    Args:
        app: BinduApplication instance

    Returns:
        Dict with storage_type, scheduler_type, task_manager_running, strict_ready
    """
    storage_type = type(app._storage).__name__ if app._storage else None
    scheduler_type = type(app._scheduler).__name__ if app._scheduler else None
    task_manager_running = app.task_manager.is_running if app.task_manager else False

    strict_ready = all(
        [
            app._storage is not None,
            app._scheduler is not None,
            task_manager_running,
        ]
    )

    return {
        "storage_type": storage_type,
        "scheduler_type": scheduler_type,
        "task_manager_running": task_manager_running,
        "strict_ready": strict_ready,
    }


def create_response_with_x402(
    request: Request,
    content: Any,
    response_type: type[Response] = JSONResponse,
    **kwargs,
) -> Response:
    """Create response and add X402 header if requested.

    Args:
        request: Starlette request
        content: Response content
        response_type: Response class to use
        **kwargs: Additional response kwargs

    Returns:
        Response with X402 header if requested
    """
    from bindu.extensions.x402.extension import (
        is_activation_requested as x402_is_requested,
        add_activation_header as x402_add_header,
    )

    resp = response_type(content=content, **kwargs)
    if x402_is_requested(request):
        resp = x402_add_header(resp)
    return resp


def validate_authentication(
    request: Request,
    client_ip: str,
    context: str = "this operation",
    request_id: Any = None,
) -> JSONResponse | None:
    """Validate authentication if enabled.

    Args:
        request: Starlette request
        client_ip: Client IP for logging
        context: Context description for error message
        request_id: Optional JSON-RPC request ID

    Returns:
        None if authenticated, error response otherwise
    """
    if not app_settings.auth.enabled:
        return None

    user_info = getattr(request.state, "user", None)
    if user_info:
        return None

    logger.warning(f"Unauthenticated {context} request from {client_ip}")
    from bindu.common.protocol.types import AuthenticationRequiredError

    code, message = extract_error_fields(AuthenticationRequiredError)
    return jsonrpc_error(
        code,
        message,
        f"Authentication required for {context}",
        request_id,
        401,
    )


def get_skill_or_error(app: Any, skill_id: str) -> tuple[Any, JSONResponse | None]:
    """Get skill by ID or return error response.

    Args:
        app: BinduApplication instance
        skill_id: Skill ID to find

    Returns:
        Tuple of (skill, error_response). One will be None.
    """
    from bindu.utils.skills import find_skill_by_id
    from bindu.common.protocol.types import SkillNotFoundError

    skills = app.manifest.skills or [] if app.manifest else []
    skill = find_skill_by_id(skills, skill_id)

    if not skill:
        logger.warning(f"Skill not found: {skill_id}")
        code, message = extract_error_fields(SkillNotFoundError)
        return None, jsonrpc_error(code, f"Skill not found: {skill_id}", status=404)

    return skill, None


def validate_payment_manager(
    app: Any, use_html: bool = False, error_html_generator: Any = None
) -> Response | None:
    """Validate payment session manager exists.

    Args:
        app: BinduApplication instance
        use_html: Whether to return HTML response
        error_html_generator: Function to generate error HTML (for HTML responses)

    Returns:
        None if manager exists, error response otherwise
    """
    if app._payment_session_manager is not None:
        return None

    if use_html:
        from starlette.responses import HTMLResponse

        error_content = (
            error_html_generator("Payment sessions not enabled")
            if error_html_generator
            else "Payment sessions not enabled"
        )
        return HTMLResponse(content=error_content, status_code=503)
    else:
        return JSONResponse(
            content={"error": "Payment sessions not enabled"}, status_code=503
        )
