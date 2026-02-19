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
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
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
        """Send a message using the A2A protocol."""
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

        config = request["params"].get("configuration", {})
        if history_length := config.get("history_length"):
            scheduler_params["history_length"] = history_length

        push_config = config.get("push_notification_config")
        if push_config and self.push_manager:
            is_long_running = config.get("long_running", False)
            await self.push_manager.register_push_config(
                task["id"], push_config, persist=is_long_running
            )

        message_metadata = message.get("metadata", {})
        if "_payment_context" in message_metadata:
            scheduler_params["payment_context"] = message_metadata["_payment_context"]
            del message["metadata"]["_payment_context"]

        await self.scheduler.run_task(scheduler_params)

        return SendMessageResponse(
            jsonrpc="2.0",
            id=request["id"],
            result=task,
        )

    async def stream_message(self, request: StreamMessageRequest):
        """Stream messages using Server-Sent Events (SSE)."""

        from starlette.responses import StreamingResponse

        message = request["params"]["message"]
        context_id = self.context_id_parser(message.get("context_id"))

        # Submit task (same pattern as send_message)
        task: Task = await self.storage.submit_task(context_id, message)

        async def stream_generator():
            try:
                # Move task to working
                await self.storage.update_task(task["id"], state="working")

                # Initial status event
                status_event = {
                    "kind": "status-update",
                    "task_id": str(task["id"]),
                    "context_id": str(context_id),
                    "status": {
                        "state": "working",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "final": False,
                }
                yield f"data: {json.dumps(status_event)}\n\n"

                # Worker-based streaming execution
                if self.workers:
                    worker = self.workers[0]

                    async for event in worker.stream_task(task["id"]):
                        if event.get("event") == "artifact-update":
                            artifact_event = {
                                "kind": "artifact-update",
                                "task_id": str(task["id"]),
                                "context_id": str(context_id),
                                "artifact": {
                                    "artifact_id": str(uuid.uuid4()),
                                    "name": "streaming_response",
                                    "parts": [
                                        {"kind": "text", "text": event["chunk"]}
                                    ],
                                },
                                "append": True,
                                "last_chunk": False,
                            }
                            yield f"data: {json.dumps(artifact_event)}\n\n"

                        elif event.get("event") == "status-update":
                            # Worker handles lifecycle internally
                            pass

                # Final completion event (SSE contract consistency)
                completion_event = {
                    "kind": "status-update",
                    "task_id": str(task["id"]),
                    "context_id": str(context_id),
                    "status": {
                        "state": "completed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "final": True,
                }
                yield f"data: {json.dumps(completion_event)}\n\n"

                await self.storage.update_task(task["id"], state="completed")

            except Exception as e:
                error_event = {
                    "kind": "status-update",
                    "task_id": str(task["id"]),
                    "context_id": str(context_id),
                    "status": {
                        "state": "failed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "final": True,
                    "error": str(e),
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                await self.storage.update_task(task["id"], state="failed")

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
        )
