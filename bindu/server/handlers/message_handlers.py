# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Message handlers for Bindu server.

This module handles message-related RPC requests including
sending messages and streaming responses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from bindu.common.protocol.types import (
    SendMessageRequest,
    SendMessageResponse,
    StreamMessageRequest,
    Task,
    TaskSendParams,
)

from bindu.utils.task_telemetry import trace_task_operation, track_active_task

from bindu.server.scheduler import Scheduler
from bindu.server.storage import Storage


@dataclass
class MessageHandlers:
    """Handles message-related RPC requests."""

    scheduler: Scheduler
    storage: Storage[Any]
    manifest: Any | None = None
    workers: list[Any] | None = None
    context_id_parser: Any = None
    push_manager: Any | None = None

    @trace_task_operation("send_message")
    @track_active_task
    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        """Send a message using the A2A protocol.

        Note: Payment enforcement is handled by X402Middleware before this method is called.
        If the request reaches here, payment has already been verified.
        Settlement will be handled by ManifestWorker when task completes.
        """
        message = request["params"]["message"]
        context_id = self.context_id_parser(message.get("context_id"))

        # Submit task to storage
        task: Task = await self.storage.submit_task(context_id, message)

        # Schedule task for execution
        scheduler_params: TaskSendParams = TaskSendParams(
            task_id=task["id"],
            context_id=context_id,
            message=message,
        )

        # Add optional configuration parameters
        config = request["params"].get("configuration", {})
        if history_length := config.get("history_length"):
            scheduler_params["history_length"] = history_length

        # A2A Protocol: Register push notification config if provided inline
        # Supports both inline (in message/send) and separate RPC registration
        push_config = config.get("push_notification_config")
        if push_config and self.push_manager:
            # Use long_running flag to determine if config should be persisted
            is_long_running = config.get("long_running", False)
            await self.push_manager.register_push_config(
                task["id"], push_config, persist=is_long_running
            )

        # Pass payment context from message metadata to worker if available
        # This is injected by the endpoint when x402 middleware verifies payment
        message_metadata = message.get("metadata", {})
        if "_payment_context" in message_metadata:
            scheduler_params["payment_context"] = message_metadata["_payment_context"]
            # Remove from message metadata to keep it clean (internal use only)
            del message["metadata"]["_payment_context"]

        await self.scheduler.run_task(scheduler_params)
        return SendMessageResponse(jsonrpc="2.0", id=request["id"], result=task)

    async def stream_message(self, request: StreamMessageRequest):
        """Stream messages using Server-Sent Events via the worker pipeline.

        This method delegates streaming to ManifestWorker.stream_task() which
        handles the full worker pipeline: state management, tracing, DID signing,
        payment settlement, and push notifications.

        Returns a StreamingResponse that yields TaskStatusUpdateEvent and
        TaskArtifactUpdateEvent as SSE data frames.

        Args:
            request: StreamMessageRequest containing message and configuration

        Returns:
            StreamingResponse with media_type="text/event-stream"
        """
        from starlette.responses import StreamingResponse

        message = request["params"]["message"]
        context_id = self.context_id_parser(message.get("context_id"))

        # Submit task to storage (same as send_message flow)
        task: Task = await self.storage.submit_task(context_id, message)

        # Build task parameters for worker pipeline
        scheduler_params: TaskSendParams = TaskSendParams(
            task_id=task["id"],
            context_id=context_id,
            message=message,
        )

        # Add optional configuration parameters
        config = request["params"].get("configuration", {})
        if history_length := config.get("history_length"):
            scheduler_params["history_length"] = history_length

        # Register push notification config if provided inline
        push_config = config.get("push_notification_config")
        if push_config and self.push_manager:
            is_long_running = config.get("long_running", False)
            await self.push_manager.register_push_config(
                task["id"], push_config, persist=is_long_running
            )

        # Pass payment context from message metadata to worker
        message_metadata = message.get("metadata", {})
        if "_payment_context" in message_metadata:
            scheduler_params["payment_context"] = message_metadata["_payment_context"]
            del message["metadata"]["_payment_context"]

        async def stream_generator():
            """Generate SSE events from worker.stream_task() async generator."""
            try:
                if self.workers:
                    worker = self.workers[0]
                    async for event in worker.stream_task(scheduler_params):
                        yield f"data: {json.dumps(event)}\n\n"
                else:
                    # No workers available — yield error event
                    error_event = {
                        "kind": "status-update",
                        "task_id": str(task["id"]),
                        "context_id": str(context_id),
                        "status": {"state": "failed"},
                        "final": True,
                        "metadata": {"error": "No workers available for streaming"},
                    }
                    yield f"data: {json.dumps(error_event)}\n\n"
                    await self.storage.update_task(task["id"], state="failed")
            except Exception as e:
                # Yield error event if stream_task() raises unexpectedly
                error_event = {
                    "kind": "status-update",
                    "task_id": str(task["id"]),
                    "context_id": str(context_id),
                    "status": {"state": "failed"},
                    "final": True,
                    "metadata": {"error": str(e)},
                }
                yield f"data: {json.dumps(error_event)}\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")
