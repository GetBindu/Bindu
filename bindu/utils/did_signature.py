"""DID signature utilities for hybrid OAuth2 + DID authentication.

This module provides utilities for signing and verifying requests using
DID-based cryptographic signatures for enhanced security.
"""

from __future__ import annotations as _annotations

import json
import time
from typing import Any, Dict, Optional

from bindu.utils.logging import get_logger

logger = get_logger("bindu.utils.did_signature")


def create_signature_payload(
    body: str | bytes | dict, did: str, timestamp: Optional[int] = None
) -> Dict[str, Any]:
    """Create signature payload for request signing.

    Args:
        body: Request body (string, bytes, or dict)
        did: Client's DID
        timestamp: Unix timestamp (defaults to current time)

    Returns:
        Signature payload dict
    """
    if timestamp is None:
        timestamp = int(time.time())

    # Convert body to string
    if isinstance(body, dict):
        body_str = json.dumps(body, sort_keys=True)
    elif isinstance(body, bytes):
        body_str = body.decode("utf-8")
    else:
        body_str = str(body)

    return {"body": body_str, "timestamp": timestamp, "did": did}


def sign_request(
    body: str | bytes | dict, did: str, did_extension, timestamp: Optional[int] = None
) -> Dict[str, str]:
    """Sign a request with DID private key.

    Args:
        body: Request body
        did: Client's DID
        did_extension: DIDExtension instance with private key
        timestamp: Unix timestamp (defaults to current time)

    Returns:
        Dict with signature headers (X-DID, X-DID-Signature, X-DID-Timestamp)
    """
    # Create signature payload
    payload = create_signature_payload(body, did, timestamp)
    payload_str = json.dumps(payload, sort_keys=True)

    # Sign with private key
    signature = did_extension.sign_message(payload_str)

    return {
        "X-DID": did,
        "X-DID-Signature": signature,
        "X-DID-Timestamp": str(payload["timestamp"]),
    }


def verify_signature(
    body: str | bytes | dict,
    signature: str,
    did: str,
    timestamp: int,
    public_key: str,
    max_age_seconds: int = 300,
) -> bool:
    """Verify DID signature on a request.

    Args:
        body: Request body
        signature: DID signature from X-DID-Signature header
        did: Client's DID from X-DID header
        timestamp: Timestamp from X-DID-Timestamp header
        public_key: Client's public key (multibase encoded)
        max_age_seconds: Maximum age of request in seconds (default 5 minutes)

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Check timestamp to prevent replay attacks
        current_time = int(time.time())
        if abs(current_time - timestamp) > max_age_seconds:
            logger.warning(
                f"Request timestamp too old: {timestamp} vs {current_time} "
                f"(max age: {max_age_seconds}s)"
            )
            return False

        # Reconstruct signature payload
        payload = create_signature_payload(body, did, timestamp)
        payload_str = json.dumps(payload, sort_keys=True)

        # Verify signature with public key
        import base58
        from nacl.signing import VerifyKey
        from nacl.exceptions import BadSignatureError

        # Decode the base58-encoded public key and signature
        try:
            public_key_bytes = base58.b58decode(public_key)
            signature_bytes = base58.b58decode(signature)

            # Create verify key from public key bytes
            verify_key = VerifyKey(public_key_bytes)

            # Verify the signature
            verify_key.verify(payload_str.encode("utf-8"), signature_bytes)
            is_valid = True
        except (BadSignatureError, Exception):
            is_valid = False

        if not is_valid:
            logger.warning(f"Invalid DID signature for {did}")

        return is_valid

    except Exception as e:
        logger.error(f"Failed to verify DID signature: {e}")
        return False


def extract_signature_headers(headers: dict) -> Optional[Dict[str, Any]]:
    """Extract DID signature headers from request.

    Args:
        headers: Request headers dict

    Returns:
        Dict with did, signature, timestamp or None if missing
    """
    did = headers.get("X-DID") or headers.get("x-did")
    signature = headers.get("X-DID-Signature") or headers.get("x-did-signature")
    timestamp_str = headers.get("X-DID-Timestamp") or headers.get("x-did-timestamp")

    if not all([did, signature, timestamp_str]):
        return None

    try:
        timestamp = int(timestamp_str)
    except (ValueError, TypeError):
        logger.warning(f"Invalid timestamp format: {timestamp_str}")
        return None

    return {"did": did, "signature": signature, "timestamp": timestamp}


def validate_timestamp(timestamp: int, max_age_seconds: int = 300) -> bool:
    """Validate request timestamp to prevent replay attacks.

    Args:
        timestamp: Unix timestamp from request
        max_age_seconds: Maximum age in seconds (default 5 minutes)

    Returns:
        True if timestamp is valid, False otherwise
    """
    current_time = int(time.time())
    age = abs(current_time - timestamp)

    if age > max_age_seconds:
        logger.warning(f"Request timestamp expired: age={age}s, max={max_age_seconds}s")
        return False

    return True


async def get_public_key_from_hydra(client_did: str, hydra_client) -> Optional[str]:
    """Get client's public key from Hydra metadata.

    Args:
        client_did: Client's DID (used as client_id)
        hydra_client: HydraClient instance

    Returns:
        Public key (multibase encoded) or None
    """
    try:
        client = await hydra_client.get_oauth_client(client_did)
        if not client:
            logger.error(f"Client not found in Hydra: {client_did}")
            return None

        public_key = client.get("metadata", {}).get("public_key")
        if not public_key:
            logger.warning(f"No public key found for client: {client_did}")
            return None

        return public_key

    except Exception as e:
        logger.error(f"Failed to get public key from Hydra: {e}")
        return None


def create_signed_request_headers(
    body: str | bytes | dict, did: str, did_extension, bearer_token: str
) -> Dict[str, str]:
    """Create complete headers for signed request with OAuth token.

    Args:
        body: Request body
        did: Client's DID
        did_extension: DIDExtension instance
        bearer_token: OAuth2 access token

    Returns:
        Dict with all required headers
    """
    # Get DID signature headers
    signature_headers = sign_request(body, did, did_extension)

    # Combine with OAuth token
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Content-Type": "application/json",
        **signature_headers,
    }

    return headers
