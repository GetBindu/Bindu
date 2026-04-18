"""ScopeBlind extension and Cedar policy evaluation."""

from __future__ import annotations

import os

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import cached_property
from pathlib import Path
from typing import Any, Literal, TypedDict

import base58
from cedar import Authorizer, Context, EntityUid, PolicySet, Request as CedarRequest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from bindu.common.protocol.types import AgentExtension, Artifact
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

from .receipt import (
    ScopeBlindReceipt,
    ScopeBlindReceiptPayload,
    build_artifact_digest,
    build_task_receipt_metadata,
    sha256_digest,
)

logger = get_logger("bindu.scopeblind_extension")


class ScopeBlindAuthorizationContext(TypedDict):
    """JSON-serializable authorization context carried through execution."""

    mode: Literal["enforce", "shadow"]
    allowed: bool
    decision: Literal["Allow", "Deny"]
    policy_hash: str
    policy_ids: list[str]
    errors: list[str]
    principal: dict[str, Any]
    action: dict[str, Any]
    resource: dict[str, Any]
    context: dict[str, Any]
    verification_key: str
    issuer: str


@dataclass(frozen=True)
class ScopeBlindDecision:
    """Internal authorization decision representation."""

    allowed: bool
    decision: Literal["Allow", "Deny"]
    policy_ids: list[str]
    errors: list[str]
    principal: dict[str, Any]
    action: dict[str, Any]
    resource: dict[str, Any]
    context: dict[str, Any]

    def to_context(
        self,
        *,
        mode: Literal["enforce", "shadow"],
        policy_hash: str,
        verification_key: str,
        issuer: str,
    ) -> ScopeBlindAuthorizationContext:
        """Convert the decision into task-safe serialized context."""
        return ScopeBlindAuthorizationContext(
            mode=mode,
            allowed=self.allowed,
            decision=self.decision,
            policy_hash=policy_hash,
            policy_ids=self.policy_ids,
            errors=self.errors,
            principal=self.principal,
            action=self.action,
            resource=self.resource,
            context=self.context,
            verification_key=verification_key,
            issuer=issuer,
        )


class ScopeBlindExtension:
    """Authorization extension that signs receipts with a dedicated key."""

    def __init__(
        self,
        mode: Literal["enforce", "shadow"],
        cedar_policies: str,
        key_dir: Path | None = None,
    ):
        """Initialize the ScopeBlind extension.

        Args:
            mode: Whether denials should block execution or be logged only
            cedar_policies: Inline Cedar policy source or a file/directory path
            key_dir: Optional directory for receipt signing keys
        """
        if mode not in ("enforce", "shadow"):
            raise ValueError("mode must be either 'enforce' or 'shadow'")
        if not cedar_policies:
            raise ValueError("cedar_policies is required")

        self.mode = mode
        self.cedar_policies = cedar_policies
        self._key_dir = Path(key_dir) if key_dir else Path(app_settings.scopeblind.pki_dir)
        self.private_key_path = self._key_dir / app_settings.scopeblind.private_key_filename
        self.public_key_path = self._key_dir / app_settings.scopeblind.public_key_filename
        self.generate_and_save_key_pair()

    def __repr__(self) -> str:
        """Return string representation of the extension."""
        return (
            f"ScopeBlindExtension(mode={self.mode}, "
            f"cedar_policies={self.cedar_policies!r})"
        )

    @cached_property
    def policy_source(self) -> str:
        """Load Cedar policy text from a string, file, or directory."""
        raw_value = self.cedar_policies.strip()
        expanded = Path(os.path.expanduser(raw_value))
        if expanded.is_file():
            return expanded.read_text(encoding="utf-8")
        if expanded.is_dir():
            policy_parts = [
                path.read_text(encoding="utf-8")
                for path in sorted(expanded.glob("*.cedar"))
            ]
            if not policy_parts:
                raise ValueError(f"No Cedar policy files found in {expanded}")
            return "\n".join(policy_parts)
        return self.cedar_policies

    @cached_property
    def policy_hash(self) -> str:
        """Stable hash of the active Cedar policy set."""
        return sha256_digest(self.policy_source)

    @cached_property
    def policy_set(self) -> PolicySet:
        """Parse the Cedar policy set once and cache it."""
        return PolicySet(self.policy_source)

    @cached_property
    def authorizer(self) -> Authorizer:
        """Shared Cedar authorizer instance."""
        return Authorizer()

    def _generate_key_pair_data(self) -> tuple[bytes, bytes]:
        """Generate a dedicated Ed25519 keypair for receipt signing."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()
        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return private_pem, public_pem

    def generate_and_save_key_pair(self) -> None:
        """Generate receipt signing keys if they do not already exist."""
        self._key_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.chmod(self._key_dir, 0o700)
        except OSError:
            logger.warning("Could not tighten ScopeBlind key dir permissions", path=str(self._key_dir))
        if self.private_key_path.exists() and self.public_key_path.exists():
            return

        private_pem, public_pem = self._generate_key_pair_data()
        self.private_key_path.write_bytes(private_pem)
        try:
            os.chmod(self.private_key_path, 0o600)
        except OSError:
            logger.warning("Could not tighten ScopeBlind private key permissions", path=str(self.private_key_path))
        self.public_key_path.write_bytes(public_pem)
        try:
            os.chmod(self.public_key_path, 0o644)
        except OSError:
            pass

    @cached_property
    def private_key(self) -> ed25519.Ed25519PrivateKey:
        """Load the private signing key."""
        key_bytes = self.private_key_path.read_bytes()
        private_key = serialization.load_pem_private_key(key_bytes, password=None)
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise ValueError("ScopeBlind private key is not Ed25519")
        return private_key

    @cached_property
    def public_key(self) -> ed25519.Ed25519PublicKey:
        """Load the public verification key."""
        key_bytes = self.public_key_path.read_bytes()
        public_key = serialization.load_pem_public_key(key_bytes)
        if not isinstance(public_key, ed25519.Ed25519PublicKey):
            raise ValueError("ScopeBlind public key is not Ed25519")
        return public_key

    @cached_property
    def public_key_base58(self) -> str:
        """Base58-encoded raw Ed25519 public key."""
        raw_bytes = self.public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return base58.b58encode(raw_bytes).decode("ascii")

    @cached_property
    def issuer(self) -> str:
        """Stable issuer identifier for receipt metadata."""
        return f"scopeblind:{self.policy_hash[:16]}"

    @cached_property
    def agent_extension(self) -> AgentExtension:
        """Get agent extension configuration for capabilities/agent card."""
        return AgentExtension(
            uri=app_settings.scopeblind.extension_uri,
            description=app_settings.scopeblind.extension_description,
            required=(self.mode == "enforce"),
            params={
                "mode": self.mode,
                "verification_key": self.public_key_base58,
                "policy_hash": self.policy_hash,
            },
        )

    def _build_principal(self, request: Any) -> tuple[EntityUid, dict[str, Any]]:
        """Build the Cedar principal from auth context or anonymous fallback."""
        user_info = getattr(request.state, "user", None)
        if isinstance(user_info, dict) and user_info.get("sub"):
            principal_kind = "Service" if user_info.get("is_m2m") else "User"
            principal_id = str(user_info["sub"])
            principal_data = {
                "entity_type": principal_kind,
                "entity_id": principal_id,
                "client_id": user_info.get("client_id", ""),
                "scopes": user_info.get("scope", []) or [],
                "authenticated": True,
            }
        else:
            principal_kind = "Anonymous"
            principal_id = "anonymous"
            principal_data = {
                "entity_type": principal_kind,
                "entity_id": principal_id,
                "client_id": "",
                "scopes": [],
                "authenticated": False,
            }

        return EntityUid(principal_kind, principal_id), principal_data

    def _build_action(self, method: str) -> tuple[EntityUid, dict[str, Any]]:
        """Build the Cedar action entity."""
        return EntityUid("Action", method), {"entity_type": "Action", "entity_id": method}

    def _build_resource(self, request: Any) -> tuple[EntityUid, dict[str, Any]]:
        """Build the Cedar resource from the request path."""
        path = getattr(request.url, "path", "/")
        return EntityUid("Route", path), {"entity_type": "Route", "entity_id": path}

    def _build_context(self, request: Any, method: str, request_data: dict[str, Any]) -> dict[str, Any]:
        """Build the JSON context passed to Cedar and receipts."""
        user_info = getattr(request.state, "user", None)
        return {
            "http_method": request.method,
            "jsonrpc_method": method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else "unknown",
            "authenticated": bool(getattr(request.state, "authenticated", False)),
            "token_scopes": (user_info.get("scope", []) if isinstance(user_info, dict) else []),
            "request_id": request_data.get("id"),
        }

    def evaluate_request(self, request: Any, method: str, request_data: dict[str, Any]) -> ScopeBlindDecision:
        """Evaluate Cedar policies for the incoming request."""
        principal_uid, principal = self._build_principal(request)
        action_uid, action = self._build_action(method)
        resource_uid, resource = self._build_resource(request)
        context_data = self._build_context(request, method, request_data)

        try:
            cedar_request = CedarRequest(
                principal=principal_uid,
                action=action_uid,
                resource=resource_uid,
                context=Context(context_data),
            )
            response = self.authorizer.is_authorized(cedar_request, self.policy_set)
            policy_ids = [str(reason) for reason in getattr(response, "reason", [])]
            errors = [str(error) for error in getattr(response, "errors", [])]
            allowed = bool(getattr(response, "allowed", False))
            decision = "Allow" if allowed else "Deny"
            return ScopeBlindDecision(
                allowed=allowed,
                decision=decision,
                policy_ids=policy_ids,
                errors=errors,
                principal=principal,
                action=action,
                resource=resource,
                context=context_data,
            )
        except Exception as error:
            logger.error("ScopeBlind policy evaluation failed", error=str(error), exc_info=True)
            return ScopeBlindDecision(
                allowed=False,
                decision="Deny",
                policy_ids=[],
                errors=[str(error)],
                principal=principal,
                action=action,
                resource=resource,
                context=context_data,
            )

    def create_receipt(
        self,
        *,
        authorization_context: ScopeBlindAuthorizationContext,
        artifacts: list[Artifact],
        task_id: Any,
        context_id: Any,
        state: str,
    ) -> ScopeBlindReceipt:
        """Create and sign a receipt for the completed task."""
        payload = ScopeBlindReceiptPayload(
            version=app_settings.scopeblind.receipt_version,
            mode=authorization_context["mode"],
            decision=authorization_context["decision"],
            issued_at=datetime.now(timezone.utc).isoformat(),
            principal=authorization_context["principal"],
            action=authorization_context["action"],
            resource=authorization_context["resource"],
            context=authorization_context["context"],
            policy_hash=authorization_context["policy_hash"],
            policy_ids=list(authorization_context.get("policy_ids", [])),
            errors=list(authorization_context.get("errors", [])),
            task_id=str(task_id) if task_id is not None else None,
            context_id=str(context_id) if context_id is not None else None,
            state=state,
            artifacts=[build_artifact_digest(artifact) for artifact in artifacts],
        )
        payload_hash = sha256_digest(payload)
        signature = self.private_key.sign(payload_hash.encode("utf-8"))
        return ScopeBlindReceipt(
            payload=payload,
            payload_hash=payload_hash,
            verification_key=self.public_key_base58,
            signature=base58.b58encode(signature).decode("ascii"),
            issuer=authorization_context.get("issuer", self.issuer),
        )

    def build_task_metadata(
        self,
        receipt: ScopeBlindReceipt,
    ) -> dict[str, Any]:
        """Build task metadata for a signed receipt."""
        return build_task_receipt_metadata(receipt)
