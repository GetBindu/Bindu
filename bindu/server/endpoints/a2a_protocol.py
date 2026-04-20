"""A2A protocol endpoint for agent-to-agent communication."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from starlette.requests import Request
from starlette.responses import Response, StreamingResponse

from bindu.common.protocol.types import (
    InternalError,
    JSONParseError,
    MethodNotFoundError,
    a2a_request_ta,
    a2a_response_ta,
)
from bindu.server.applications import BinduApplication
from bindu.settings import app_settings
from bindu.utils.logging import get_logger
from .utils import (
    extract_error_fields,
    get_client_ip,
    jsonrpc_error,
    validate_authentication,
)
from bindu.extensions.x402.extension import (
    is_activation_requested as x402_is_requested,
    add_activation_header as x402_add_header,
)

logger = get_logger("bindu.server.endpoints.a2a_protocol")


def _attach_payment_context(request: Request, a2a_request: Any, method: str) -> None:
    """Attach payment context to message metadata if available.

    Payment context is passed through the metadata field in params.
    All three state fields are set atomically by X402Middleware only after
    successful payment validation. Use explicit ``is not None`` guards so
    that a falsy-but-present value (e.g. zero-amount payload) is not
    accidentally skipped.

    Args:
        request: Starlette request with payment state
        a2a_request: A2A request dict to modify
        method: Request method name
    """
    if method != "message/send":
        return

    # Extract payment state from request
    payment_payload = getattr(request.state, "payment_payload", None)
    payment_requirements = getattr(request.state, "payment_requirements", None)
    verify_response = getattr(request.state, "verify_response", None)

    # All three must be present
    if not all(
        [
            payment_payload is not None,
            payment_requirements is not None,
            verify_response is not None,
        ]
    ):
        return

    # Ensure message exists in params
    if "params" not in a2a_request or "message" not in a2a_request["params"]:
        return

    msg_obj = a2a_request["params"]["message"]
    msg_obj.setdefault("metadata", {})

    try:
        msg_obj["metadata"]["_payment_context"] = {
            "payment_payload": _serialize_state_obj(payment_payload),
            "payment_requirements": _serialize_state_obj(payment_requirements),
            "verify_response": _serialize_state_obj(verify_response),
        }
    except Exception as ser_err:
        # Serialization failure must not abort the request;
        # log and continue without attaching the payment context.
        logger.warning(
            f"Failed to serialize payment context into message metadata "
            f"– payment context will be omitted: {ser_err}"
        )


def _serialize_state_obj(obj: Any) -> dict:
    """Safely serialize a payment state object to a plain dict.

    Tries, in order:
    1. Pydantic ``model_dump()``
    2. ``dataclasses.asdict()`` for dataclass instances
    3. ``dict()`` coercion as a last resort

    Raises:
        TypeError: propagated from ``dict()`` if the object is not coercible
            to a mapping (i.e. does not implement ``keys()``/``__getitem__``).
        RuntimeError: propagated from any of the above strategies if the
            object raises during serialization.
    """
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    return dict(obj)


async def agent_run_endpoint(app: BinduApplication, request: Request) -> Response:
    """Handle A2A protocol requests for agent-to-agent communication.

    Protocol Behavior:
    1. The server will always either send a "submitted" or a "failed" on `tasks/send`.
        Never a "completed" on the first message.
    2. There are three possible ends for the task:
        2.1. The task was "completed" successfully.
        2.2. The task was "canceled".
        2.3. The task "failed".
    3. The server will send a "working" on the first chunk on `tasks/pushNotification/get`.
    """
    client_ip = get_client_ip(request)
    request_id = None

    try:
        data = await request.body()

        try:
            a2a_request = a2a_request_ta.validate_json(data)
        except Exception as e:
            logger.warning(f"Invalid A2A request from {client_ip}: {e}")
            code, message = extract_error_fields(JSONParseError)
            return jsonrpc_error(code, message, str(e))

        method = a2a_request.get("method")
        request_id = a2a_request.get("id")

        logger.debug(f"A2A request from {client_ip}: method={method}, id={request_id}")

        # Authentication / Authorization guard
        auth_error = validate_authentication(
            request, client_ip, "agent execution", request_id
        )
        if auth_error:
            return auth_error

        # Permission checks (if authentication passed)
        user_info = None
        if app_settings.auth.enabled:
            # Get user info from request state (set by auth middleware)
            user_info = getattr(request.state, "user", None)

            # if permission checks are enabled, ensure the token has required scope
            if app_settings.auth.require_permissions:
                required_scopes = app_settings.auth.permissions.get(method, [])
                if required_scopes and user_info:
                    token_scopes = user_info.get("scope", []) or []
                    if not any(scope in token_scopes for scope in required_scopes):
                        logger.warning(
                            f"Insufficient permissions for method {method} from {client_ip}"
                        )
                        from bindu.common.protocol.types import (
                            InsufficientPermissionsError,
                        )

                        code, message = extract_error_fields(
                            InsufficientPermissionsError
                        )
                        return jsonrpc_error(
                            code,
                            message,
                            f"Missing required permissions: {required_scopes}",
                            request_id,
                            403,
                        )

        # Resolve the authenticated caller identity used for task/context
        # ownership. ``client_id`` is the Hydra OAuth client — the same value
        # used elsewhere in the auth middleware for DID matching. ``None``
        # means auth is disabled or the caller has no client_id; rows created
        # by such callers end up with ``owner_did=NULL`` and are accessible
        # only to other unauthenticated callers once Phase 2 enforcement
        # lands.
        caller_did: str | None = None
        if user_info is not None:
            client_id = user_info.get("client_id")
            if isinstance(client_id, str) and client_id:
                caller_did = client_id

        handler_name = app_settings.agent.method_handlers.get(method)
        if handler_name is None:
            logger.warning(f"Unsupported A2A method '{method}' from {client_ip}")
            code, message = extract_error_fields(MethodNotFoundError)
            return jsonrpc_error(
                code, message, f"Method '{method}' is not implemented", request_id, 404
            )

        handler = getattr(app.task_manager, handler_name)

        # Attach payment context to message metadata if available
        _attach_payment_context(request, a2a_request, method)

        jsonrpc_response = await handler(a2a_request, caller_did=caller_did)

        logger.debug(f"A2A response to {client_ip}: method={method}, id={request_id}")

        # FIX: Strictly check for StreamingResponse to prevent bypassing JSON-RPC
        if isinstance(jsonrpc_response, StreamingResponse):
            if x402_is_requested(request):
                jsonrpc_response = x402_add_header(jsonrpc_response)
            return jsonrpc_response

        resp = Response(
            content=a2a_response_ta.dump_json(
                jsonrpc_response, by_alias=True, serialize_as_any=True
            ),
            media_type="application/json",
        )

        if x402_is_requested(request):
            resp = x402_add_header(resp)

        return resp

    except Exception as e:
        logger.error(f"Error processing A2A request from {client_ip}", exc_info=True)
        code, message = extract_error_fields(InternalError)
        return jsonrpc_error(code, message, str(e), request_id, 500)
