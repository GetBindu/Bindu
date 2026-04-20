"""BinduService gRPC implementation — handles agent registration from SDKs.

When a TypeScript/Kotlin/Rust SDK calls RegisterAgent, this service:
1. Deserializes the config JSON
2. Converts proto SkillDefinitions to inline skill dicts
3. Creates a GrpcAgentClient pointing to the SDK's callback address
4. Delegates to _bindufy_core() which handles DID, auth, x402, manifest,
   BinduApplication, and starts uvicorn in a background thread
5. Returns the agent_id, DID, and A2A endpoint URL

The _bindufy_core() function is the same code path as Python bindufy(),
ensuring DRY — there is exactly one place that handles agent setup.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import grpc

from bindu.grpc.client import GrpcAgentClient
from bindu.grpc.generated import agent_handler_pb2, agent_handler_pb2_grpc
from bindu.grpc.registry import AgentRegistry
from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.grpc.service")


def _proto_skills_to_dicts(
    skills: list[agent_handler_pb2.SkillDefinition],
) -> list[dict]:
    """Convert proto SkillDefinition messages to inline skill dicts.

    The inline dict format is already supported by load_skills() in the core.
    Each skill dict contains the parsed content so the core doesn't need
    filesystem access to the SDK's project directory.

    Args:
        skills: List of proto SkillDefinition messages from the SDK.

    Returns:
        List of skill dicts compatible with create_manifest().
    """
    result = []
    for skill in skills:
        skill_dict = {
            "name": skill.name,
            "description": skill.description,
            "tags": list(skill.tags),
            "input_modes": list(skill.input_modes),
            "output_modes": list(skill.output_modes),
        }
        if skill.version:
            skill_dict["version"] = skill.version
        if skill.author:
            skill_dict["author"] = skill.author
        if skill.raw_content:
            skill_dict["raw_content"] = skill.raw_content
            skill_dict["format"] = skill.format or "yaml"
        result.append(skill_dict)
    return result


class BinduServiceImpl(agent_handler_pb2_grpc.BinduServiceServicer):
    """gRPC servicer for BinduService — handles SDK registration and lifecycle.

    This runs on the Bindu core's gRPC server (port 3774). SDKs connect to
    this service to register their agents, send heartbeats, and unregister.

    Attributes:
        registry: Thread-safe agent registry for tracking registered agents.
    """

    def __init__(self, registry: AgentRegistry) -> None:  # noqa: D107
        self.registry = registry

    def RegisterAgent(
        self,
        request: agent_handler_pb2.RegisterAgentRequest,
        context: grpc.ServicerContext,
    ) -> agent_handler_pb2.RegisterAgentResponse:
        """Register a remote agent and start its A2A HTTP server.

        This method:
        1. Parses the config JSON from the SDK
        2. Creates a GrpcAgentClient for the SDK's callback address
        3. Calls _bindufy_core() to run the full setup (DID, auth, x402, etc.)
        4. Starts uvicorn in a background thread
        5. Returns agent identity and URL

        Args:
            request: RegisterAgentRequest with config_json, skills, and callback.
            context: gRPC servicer context.

        Returns:
            RegisterAgentResponse with agent_id, DID, and A2A URL.
        """
        try:
            # 1. Parse config from JSON
            config = json.loads(request.config_json)
            logger.info(
                f"RegisterAgent received for '{config.get('name', 'unknown')}' "
                f"with callback at {request.grpc_callback_address}"
            )

            # 2. Convert proto skills to inline dicts
            skills = _proto_skills_to_dicts(list(request.skills))

            # 3. Create GrpcAgentClient as the handler callable
            grpc_client = GrpcAgentClient(
                callback_address=request.grpc_callback_address,
                timeout=app_settings.grpc.handler_timeout,
            )

            # 4. Determine key directory for this agent
            agent_name = config.get("name", "unknown")
            key_dir = Path(f".bindu/agents/{agent_name}")
            key_dir.mkdir(parents=True, exist_ok=True)

            # 5. Run the full bindufy logic via _bindufy_core
            #    This is the SAME code path as Python bindufy() — DRY
            from bindu.penguin.bindufy import _bindufy_core

            manifest = _bindufy_core(
                config=config,
                handler_callable=grpc_client,
                run_server=True,
                key_dir=key_dir,
                launch=False,
                caller_dir=key_dir,
                skills_override=skills,
                skip_handler_validation=True,
                run_server_in_background=True,  # Don't block the gRPC call
            )

            # 6. Register in our registry
            self.registry.register(
                agent_id=str(manifest.id),
                grpc_callback_address=request.grpc_callback_address,
                manifest=manifest,
            )

            logger.info(
                f"Agent '{agent_name}' registered successfully: "
                f"id={manifest.id}, did={manifest.did_extension.did}, "
                f"url={manifest.url}"
            )

            return agent_handler_pb2.RegisterAgentResponse(
                success=True,
                agent_id=str(manifest.id),
                did=str(manifest.did_extension.did),
                agent_url=manifest.url,
            )

        except json.JSONDecodeError as e:
            error_msg = f"Invalid config_json: {e}"
            logger.error(error_msg)
            return agent_handler_pb2.RegisterAgentResponse(
                success=False, error=error_msg
            )
        except Exception as e:
            error_msg = f"Registration failed: {e}"
            logger.error(error_msg, exc_info=True)
            return agent_handler_pb2.RegisterAgentResponse(
                success=False, error=error_msg
            )

    def Heartbeat(
        self,
        request: agent_handler_pb2.HeartbeatRequest,
        context: grpc.ServicerContext,
    ) -> agent_handler_pb2.HeartbeatResponse:
        """Process a heartbeat from a registered SDK agent.

        Args:
            request: HeartbeatRequest with agent_id and timestamp.
            context: gRPC servicer context.

        Returns:
            HeartbeatResponse with acknowledgment.
        """
        updated = self.registry.update_heartbeat(request.agent_id)
        if not updated:
            logger.warning(f"Heartbeat from unknown agent: {request.agent_id}")
        return agent_handler_pb2.HeartbeatResponse(
            acknowledged=updated,
            server_timestamp=int(time.time() * 1000),
        )

    def UnregisterAgent(
        self,
        request: agent_handler_pb2.UnregisterAgentRequest,
        context: grpc.ServicerContext,
    ) -> agent_handler_pb2.UnregisterAgentResponse:
        """Unregister an agent and clean up resources.

        Args:
            request: UnregisterAgentRequest with agent_id.
            context: gRPC servicer context.

        Returns:
            UnregisterAgentResponse with success status.
        """
        # Close the GrpcAgentClient connection if it exists
        entry = self.registry.get(request.agent_id)
        if entry and hasattr(entry.manifest.run, "close"):
            close_fn = getattr(entry.manifest.run, "close")
            close_fn()

        removed = self.registry.unregister(request.agent_id)
        if removed:
            logger.info(f"Agent {request.agent_id} unregistered successfully")
        return agent_handler_pb2.UnregisterAgentResponse(
            success=removed,
            error="" if removed else f"Agent {request.agent_id} not found",
        )
