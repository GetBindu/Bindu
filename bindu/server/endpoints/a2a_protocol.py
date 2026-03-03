"""A2A protocol endpoint for agent-to-agent communication."""

from __future__ import annotations

from starlette.requests import Request
from starlette.responses import Response

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
from bindu.utils.request_utils import extract_error_fields, get_client_ip, jsonrpc_error
from bindu.extensions.x402.extension import (
    is_activation_requested as x402_is_requested,
    add_activation_header as x402_add_header,
)

logger = get_logger("bindu.server.endpoints.a2a_protocol")


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

        # ---------------------------------------------------------------------
        # Authentication / Authorization guard
        # ---------------------------------------------------------------------
        if app_settings.auth.enabled:
            # verify middleware has attached user context (if middleware was used)
            user_info = getattr(request.state, "user_info", None)
            if not user_info:
                # no authentication data, reject immediately
                logger.warning(f"Unauthenticated request for {method} from {client_ip}")
                from bindu.common.protocol.types import AuthenticationRequiredError

                code, message = extract_error_fields(AuthenticationRequiredError)
                return jsonrpc_error(
                    code,
                    message,
                    "Authentication required for agent execution",
                    request_id,
                    401,
                )

            # if permission checks are enabled, ensure the token has required scope
            if app_settings.auth.require_permissions:
                required_scopes = app_settings.auth.permissions.get(method, [])
                if required_scopes:
                    token_scopes = user_info.get("scope", []) or []
                    if not any(scope in token_scopes for scope in required_scopes):
                        logger.warning(
                            f"Insufficient permissions for method {method} from {client_ip}"
                        )
                        from bindu.common.protocol.types import InsufficientPermissionsError

                        code, message = extract_error_fields(InsufficientPermissionsError)
                        return jsonrpc_error(
                            code,
                            message,
                            f"Missing required permissions: {required_scopes}",
                            request_id,
                            403,
                        )
        
        handler_name = app_settings.agent.method_handlers.get(method)
        if handler_name is None:
            logger.warning(f"Unsupported A2A method '{method}' from {client_ip}")
            code, message = extract_error_fields(MethodNotFoundError)
            return jsonrpc_error(
                code, message, f"Method '{method}' is not implemented", request_id, 404
            )

        handler = getattr(app.task_manager, handler_name)

        # Pass payment details from middleware to handler if available
        # Payment context is passed through the metadata field in params
        if method == "message/send":
            payment_payload = getattr(request.state, "payment_payload", None)
            payment_requirements = getattr(request.state, "payment_requirements", None)
            verify_response = getattr(request.state, "verify_response", None)

            if payment_payload and payment_requirements and verify_response:
                if "params" in a2a_request and "message" in a2a_request["params"]:
                    message = a2a_request["params"]["message"]
                    message.setdefault("metadata", {})

                    from dataclasses import asdict, is_dataclass

                    def serialize_to_dict(obj):
                        if hasattr(obj, "model_dump"):
                            return obj.model_dump()
                        elif is_dataclass(obj):
                            return asdict(obj)
                        return dict(obj)

                    message["metadata"]["_payment_context"] = {
                        "payment_payload": serialize_to_dict(payment_payload),
                        "payment_requirements": serialize_to_dict(payment_requirements),
                        "verify_response": serialize_to_dict(verify_response),
                    }

        jsonrpc_response = await handler(a2a_request)

        logger.debug(f"A2A response to {client_ip}: method={method}, id={request_id}")

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
