"""A2A protocol endpoint for agent-to-agent communication."""

from __future__ import annotations

import importlib
import json
from uuid import UUID, uuid4
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.common.protocol.types import (
    InternalError,
    InvalidRequestError,
    JSONParseError,
    MethodNotFoundError,
    a2a_request_ta,
    a2a_response_ta,
)
from bindu.server.applications import BinduApplication
from bindu.settings import app_settings
from bindu.server.middleware.a2a import (
    A2AMiddleware,
    build_jsonrpc_error_response,
)
from bindu.utils.logging import get_logger
from bindu.utils.request_utils import extract_error_fields, get_client_ip
from bindu.extensions.x402.extension import (
    is_activation_requested as x402_is_requested,
    add_activation_header as x402_add_header,
)

logger = get_logger("bindu.server.endpoints.a2a_protocol")

_A2A_MIDDLEWARE_CACHE: dict[tuple[str, ...], list[A2AMiddleware]] = {}


def _load_a2a_middlewares() -> list[A2AMiddleware]:
    """Load middleware instances configured for A2A processing."""
    paths = tuple(app_settings.agent.a2a_middlewares)
    if not paths:
        return []
    cached = _A2A_MIDDLEWARE_CACHE.get(paths)
    if cached is not None:
        return cached

    middlewares: list[A2AMiddleware] = []
    for path in paths:
        module_path, class_name = path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        middleware_cls = getattr(module, class_name)
        middlewares.append(middleware_cls())

    _A2A_MIDDLEWARE_CACHE[paths] = middlewares
    return middlewares


async def _run_after_response(
    middlewares: list[A2AMiddleware],
    request: Request,
    response: Response,
) -> Response:
    for middleware in middlewares:
        result = await middleware.after_response(request, response)
        if isinstance(result, Response):
            response = result
    return response


async def _run_on_error(
    middlewares: list[A2AMiddleware],
    request: Request,
    error: Exception | Response,
) -> Response | None:
    response: Response | None = error if isinstance(error, Response) else None
    for middleware in reversed(middlewares):
        result = await middleware.on_error(request, error)
        if isinstance(result, Response):
            response = result
    return response


def validate_a2a_request_payload(
    data: bytes | dict,
    correlation_id: str | None = None,
) -> tuple[dict | None, JSONResponse | None]:
    """Validate incoming A2A JSON-RPC payloads before dispatch."""
    if isinstance(data, dict):
        raw_payload = data
    else:
        try:
            raw_payload = json.loads(data)
        except json.JSONDecodeError as exc:
            code, message = extract_error_fields(JSONParseError)
            return None, build_jsonrpc_error_response(
                code, message, str(exc), correlation_id=correlation_id
            )

    if not isinstance(raw_payload, dict):
        code, message = extract_error_fields(InvalidRequestError)
        return None, build_jsonrpc_error_response(
            code, message, "Expected object", correlation_id=correlation_id
        )

    if "method" not in raw_payload:
        code, message = extract_error_fields(InvalidRequestError)
        return None, build_jsonrpc_error_response(
            code, message, "Missing 'method'", correlation_id=correlation_id
        )

    request_id = raw_payload.get("id")
    payload_for_validation = raw_payload
    if "id" in raw_payload:
        try:
            UUID(str(raw_payload.get("id")))
        except (TypeError, ValueError):
            payload_for_validation = dict(raw_payload)
            payload_for_validation["id"] = uuid4()

    try:
        a2a_request = a2a_request_ta.validate_python(payload_for_validation)
    except Exception as exc:
        code, message = extract_error_fields(InvalidRequestError)
        return (
            None,
            build_jsonrpc_error_response(
                code,
                message,
                str(exc),
                request_id,
                correlation_id=correlation_id,
            ),
        )

    if payload_for_validation is not raw_payload:
        a2a_request["id"] = request_id

    return a2a_request, None


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
    middlewares = _load_a2a_middlewares()
    executed: list[A2AMiddleware] = []
    method: str | None = None
    payload_request_id: str | int | None = None

    try:
        data = await request.body()
        parse_failed = False
        try:
            raw_payload = json.loads(data)
        except json.JSONDecodeError as exc:
            parse_failed = True
            raw_payload = {}
            parse_error = exc

        try:
            for middleware in middlewares:
                executed.append(middleware)
                result = await middleware.before_request(request, raw_payload)
                if isinstance(result, Response):
                    return await _run_after_response(executed, request, result)
        except Exception as exc:
            request.state.error_type = "middleware_error"
            code, message = extract_error_fields(InternalError)
            response = build_jsonrpc_error_response(
                code, message, str(exc), status=500
            )
            handled = await _run_on_error(executed, request, response)
            return handled or response

        if parse_failed:
            code, message = extract_error_fields(JSONParseError)
            response = build_jsonrpc_error_response(
                code, message, str(parse_error), correlation_id=getattr(request.state, "request_id", None)
            )
            request.state.error_type = "validation"
            error_response = await _run_on_error(executed, request, response)
            return error_response or response

        if not isinstance(raw_payload, dict):
            code, message = extract_error_fields(InvalidRequestError)
            response = build_jsonrpc_error_response(
                code, message, "Expected object", correlation_id=getattr(request.state, "request_id", None)
            )
            request.state.error_type = "validation"
            error_response = await _run_on_error(executed, request, response)
            return error_response or response

        if "method" not in raw_payload:
            code, message = extract_error_fields(InvalidRequestError)
            response = build_jsonrpc_error_response(
                code, message, "Missing 'method'", correlation_id=getattr(request.state, "request_id", None)
            )
            request.state.error_type = "validation"
            error_response = await _run_on_error(executed, request, response)
            return error_response or response

        correlation_id = getattr(request.state, "request_id", None)
        a2a_request, error_response = validate_a2a_request_payload(
            raw_payload, correlation_id=correlation_id
        )
        if error_response is not None:
            logger.warning("Invalid A2A request from %s", client_ip)
            request.state.error_type = "validation"
            handled = await _run_on_error(executed, request, error_response)
            return handled or error_response

        method = a2a_request.get("method")
        payload_request_id = a2a_request.get("id")
        request.state.a2a_method = method

        logger.debug(
            f"A2A request from {client_ip}: method={method}, id={payload_request_id}"
        )

        handler_name = app_settings.agent.method_handlers.get(method)
        if handler_name is None:
            logger.warning(
                f"Unsupported A2A method '{method}' from {client_ip}")
            code, message = extract_error_fields(MethodNotFoundError)
            response = build_jsonrpc_error_response(
                code,
                message,
                f"Method '{method}' is not implemented",
                payload_request_id,
                correlation_id=correlation_id,
                status=404,
            )
            request.state.error_type = "method_not_found"
            handled = await _run_on_error(executed, request, response)
            return handled or response

        handler = getattr(app.task_manager, handler_name)

        # Pass payment details from middleware to handler if available
        # Payment context is passed through the metadata field in params
        if hasattr(request.state, "payment_payload") and method == "message/send":
            # Inject payment context into message metadata
            if "params" in a2a_request and "message" in a2a_request["params"]:
                message = a2a_request["params"]["message"]
                if "metadata" not in message:
                    message["metadata"] = {}

                # Add payment context to message metadata (internal use only)
                # Serialize Pydantic models and dataclasses to dicts for JSON compatibility
                from dataclasses import asdict, is_dataclass

                def serialize_to_dict(obj):
                    """Serialize Pydantic models or dataclasses to dict."""
                    if hasattr(obj, "model_dump"):
                        return obj.model_dump()
                    elif is_dataclass(obj):
                        return asdict(obj)
                    else:
                        return dict(obj)

                message["metadata"]["_payment_context"] = {
                    "payment_payload": serialize_to_dict(request.state.payment_payload),
                    "payment_requirements": serialize_to_dict(
                        request.state.payment_requirements
                    ),
                    "verify_response": serialize_to_dict(request.state.verify_response),
                }

        jsonrpc_response = await handler(a2a_request)

        logger.debug(
            f"A2A response to {client_ip}: method={method}, id={payload_request_id}"
        )

        resp = Response(
            content=a2a_response_ta.dump_json(
                jsonrpc_response, by_alias=True, serialize_as_any=True
            ),
            media_type="application/json",
        )

        if x402_is_requested(request):
            resp = x402_add_header(resp)

        return await _run_after_response(executed, request, resp)

    except Exception as e:
        logger.error(
            f"Error processing A2A request from {client_ip}", exc_info=True)
        code, message = extract_error_fields(InternalError)
        response = build_jsonrpc_error_response(
            code,
            message,
            str(e),
            payload_request_id,
            correlation_id=getattr(request.state, "request_id", None),
            status=500,
        )
        request.state.error_type = "internal"
        handled = await _run_on_error(executed, request, response)
        return handled or response
