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

import anyio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from bindu.common.protocol.types import (
    SendMessageRequest,
    SendMessageResponse,
    StreamMessageRequest,
    Task,
    TaskSendParams,
)
from bindu.settings import app_settings

from bindu.utils.logging import get_logger
from bindu.utils.task_telemetry import trace_task_operation, track_active_task

from bindu.server.scheduler import Scheduler
from bindu.server.storage import Storage

logger = get_logger("bindu.server.handlers.message_handlers")


@dataclass
class MessageHandlers:
    """Handles message-related RPC requests."""

    scheduler: Scheduler
    storage: Storage[Any]
    manifest: Any | None = None
    workers: list[Any] | None = None
    context_id_parser: Any = None
    push_manager: Any | None = None

    async def _submit_and_schedule_task(
        self, request_params: dict[str, Any]
    ) -> tuple[Task, UUID]:
        """Submit task to storage and schedule it with shared send/stream logic."""
        message = request_params["message"]
        context_id = self.context_id_parser(message.get("context_id"))

        task: Task = await self.storage.submit_task(context_id, message)

        scheduler_params: TaskSendParams = TaskSendParams(
            task_id=task["id"],
            context_id=context_id,
            message=message,
        )

        config = request_params.get("configuration", {})
        if history_length := config.get("history_length"):
            scheduler_params["history_length"] = history_length

        push_config = config.get("push_notification_config")
        if push_config and self.push_manager:
            is_long_running = config.get("long_running", False)
            await self.push_manager.register_push_config(
                task["id"], push_config, persist=is_long_running
            )

        message_metadata = message.get("metadata", {})
        if (
            isinstance(message_metadata, dict)
            and "_payment_context" in message_metadata
        ):
            # Move payment context to scheduler params and strip it from the
            # message metadata so it is not persisted or forwarded to the agent
            scheduler_params["payment_context"] = message_metadata["_payment_context"]
            del message_metadata["_payment_context"]

        await self.scheduler.run_task(scheduler_params)
        return task, context_id

    @staticmethod
    def _to_jsonable(value: Any) -> Any:
        """Convert UUID-rich protocol objects into JSON-serializable values."""
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, dict):
            return {k: MessageHandlers._to_jsonable(v) for k, v in value.items()}
        if isinstance(value, list):
            return [MessageHandlers._to_jsonable(v) for v in value]
        return value

    @staticmethod
    def _sse_event(payload: dict[str, Any]) -> str:
        """Serialize an SSE event payload."""
        return f"data: {json.dumps(MessageHandlers._to_jsonable(payload))}\n\n"

    @trace_task_operation("send_message")
    @track_active_task
    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        """Send a message using the A2A protocol.

        Note: Payment enforcement is handled by X402Middleware before this method is called.
        If the request reaches here, payment has already been verified.
        Settlement will be handled by ManifestWorker when task completes.
        """
        task, _ = await self._submit_and_schedule_task(request["params"])
        return SendMessageResponse(jsonrpc="2.0", id=request["id"], result=task)

    @trace_task_operation("stream_message")
    @track_active_task
    async def stream_message(self, request: StreamMessageRequest):
        """Stream messages using Server-Sent Events.

        Uses the same submit + scheduler execution path as message/send to keep
        lifecycle and error handling consistent.
        """
        from starlette.responses import StreamingResponse

        task, context_id = await self._submit_and_schedule_task(request["params"])

        async def stream_generator():
            """Stream task status and artifact events from storage updates."""
            seen_status = task["status"]["state"]
            seen_artifact_ids: set[str] = set()
            cancelled_exc = anyio.get_cancelled_exc_class()
            poll_interval = max(app_settings.agent.stream_poll_interval_seconds, 0.01)
            missing_retries = max(app_settings.agent.stream_missing_task_retries, 0)
            missing_retry_delay = max(
                app_settings.agent.stream_missing_task_retry_delay_seconds,
                0.0,
            )

            submitted_event = {
                "kind": "status-update",
                "task_id": str(task["id"]),
                "context_id": str(context_id),
                "status": task["status"],
                "final": False,
            }
            yield self._sse_event(submitted_event)

            try:
                while True:
                    loaded_task = await self.storage.load_task(task["id"])
                    if loaded_task is None:
                        for _ in range(missing_retries):
                            await anyio.sleep(missing_retry_delay)
                            loaded_task = await self.storage.load_task(task["id"])
                            if loaded_task is not None:
                                break
                    if loaded_task is None:
                        missing_event = {
                            "kind": "status-update",
                            "task_id": str(task["id"]),
                            "context_id": str(context_id),
                            "status": {
                                "state": "failed",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                            "final": True,
                            "error": f"Task {task['id']} not found while streaming",
                        }
                        yield self._sse_event(missing_event)
                        return

                    status = loaded_task["status"]["state"]
                    if status != seen_status:
                        status_event = {
                            "kind": "status-update",
                            "task_id": str(task["id"]),
                            "context_id": str(context_id),
                            "status": loaded_task["status"],
                            "final": status in app_settings.agent.terminal_states,
                        }
                        yield self._sse_event(status_event)
                        seen_status = status

                    for artifact in loaded_task.get("artifacts", []):
                        artifact_id = str(artifact["artifact_id"])
                        if artifact_id in seen_artifact_ids:
                            continue
                        seen_artifact_ids.add(artifact_id)

                        artifact_event = {
                            "kind": "artifact-update",
                            "task_id": str(task["id"]),
                            "context_id": str(context_id),
                            "artifact": artifact,
                            "append": artifact.get("append", False),
                            "last_chunk": artifact.get("last_chunk", False),
                        }
                        yield self._sse_event(artifact_event)

                    if status in app_settings.agent.terminal_states:
                        return

                    if status in ("input-required", "auth-required"):
                        # Re-check once before returning to avoid missing a quick
                        # transition into a terminal state.
                        latest_task = await self.storage.load_task(task["id"])
                        if latest_task:
                            latest_status = latest_task["status"]["state"]
                            if latest_status != seen_status:
                                yield self._sse_event(
                                    {
                                        "kind": "status-update",
                                        "task_id": str(task["id"]),
                                        "context_id": str(context_id),
                                        "status": latest_task["status"],
                                        "final": latest_status
                                        in app_settings.agent.terminal_states,
                                    }
                                )
                                seen_status = latest_status
                                if latest_status in app_settings.agent.terminal_states:
                                    return
                        return

                    await anyio.sleep(poll_interval)
            except cancelled_exc:
                logger.debug(f"Streaming client disconnected for task {task['id']}")
                return
            except Exception as e:
                logger.error(
                    f"Unhandled stream error for task {task['id']}: {e}", exc_info=True
                )
                timestamp = datetime.now(timezone.utc).isoformat()
                current_state = "failed"
                try:
                    loaded_task = await self.storage.load_task(task["id"])
                except Exception as load_err:
                    loaded_task = None
                    logger.error(
                        f"Failed to load task {task['id']} during stream error handling: {load_err}",
                        exc_info=True,
                    )

                if loaded_task:
                    current_state = loaded_task["status"]["state"]
                    timestamp = loaded_task["status"]["timestamp"]
                    if current_state not in app_settings.agent.terminal_states:
                        try:
                            updated = await self.storage.update_task(
                                task["id"], state="failed"
                            )
                            if updated and "status" in updated:
                                current_state = updated["status"]["state"]
                                timestamp = updated["status"]["timestamp"]
                        except Exception as update_err:
                            logger.error(
                                f"Failed to update task {task['id']} to failed state during error handling: {update_err}",
                                exc_info=True,
                            )

                error_event = {
                    "kind": "status-update",
                    "task_id": str(task["id"]),
                    "context_id": str(context_id),
                    "status": {
                        "state": current_state,
                        "timestamp": timestamp,
                    },
                    "final": current_state in app_settings.agent.terminal_states,
                    "error": str(e),
                }
                yield self._sse_event(error_event)

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )
