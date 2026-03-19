"""DID resolution and agent information endpoints."""

from __future__ import annotations

from typing import Optional

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from bindu.common.protocol.types import (
    InternalError,
    InvalidParamsError,
    JSONParseError,
)
from bindu.server.applications import BinduApplication
from bindu.utils.logging import get_logger
from .utils import (
    handle_endpoint_errors,
    extract_error_fields,
    get_client_ip,
    jsonrpc_error,
    validate_manifest,
)

logger = get_logger("bindu.server.endpoints.did_endpoints")


def _did_not_found_error(did: str, reason: str, client_ip: str) -> Response:
    """Return DID not found error response.

    Args:
        did: Requested DID
        reason: Reason for error (for logging)
        client_ip: Client IP for logging

    Returns:
        JSON-RPC error response
    """
    logger.warning(f"{reason} (requested by {client_ip})")
    code, message = extract_error_fields(InternalError)
    return jsonrpc_error(code, message, f"DID '{did}' not found", status=404)


@handle_endpoint_errors("DID resolve")
async def did_resolve_endpoint(app: BinduApplication, request: Request) -> Response:
    """Resolve DID and return full W3C-compliant DID document."""
    client_ip = get_client_ip(request)

    # Get DID from query param (GET) or JSON body (POST).
    # Calling request.json() on a GET request raises an exception because
    # GET requests carry no body — always check the method first.
    did: Optional[str] = None
    if request.method == "GET":
        did = request.query_params.get("did")
    else:
        try:
            data = await request.json()
            did = data.get("did")
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid JSON in DID resolve request from {client_ip}: {e}")
            code, message = extract_error_fields(JSONParseError)
            return jsonrpc_error(code, message, str(e))

    if not did:
        logger.warning(f"DID resolve request missing 'did' parameter from {client_ip}")
        code, message = extract_error_fields(InvalidParamsError)
        return jsonrpc_error(code, message, "Missing 'did' parameter")

    # Ensure manifest exists
    error_resp = validate_manifest(app, client_ip, use_jsonrpc=True)
    if error_resp:
        return error_resp

    # Get DID extension
    did_extension = app.manifest.did_extension

    # Validate DID extension exists and has 'did' attribute
    if not did_extension or not hasattr(did_extension, "did"):
        return _did_not_found_error(did, "DID extension not configured", client_ip)

    # Check if requested DID matches our DID
    if did_extension.did != did:
        return _did_not_found_error(
            did,
            f"DID mismatch - requested: {did}, our DID: {did_extension.did}",
            client_ip,
        )

    # Validate DID extension has required method
    if not hasattr(did_extension, "get_did_document"):
        return _did_not_found_error(
            did, "DID extension missing 'get_did_document' method", client_ip
        )

    logger.debug(f"Resolving DID {did} for {client_ip}")
    did_document = did_extension.get_did_document()
    return JSONResponse(content=did_document)
