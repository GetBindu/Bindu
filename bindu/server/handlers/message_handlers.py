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

        message_metadata = message.get("metadata")

        if message_metadata is None:
            message_metadata = {}
            message["metadata"] = message_metadata

        elif not isinstance(message_metadata, dict):
            logger.warning(
                "Invalid metadata type received in message",
                extra={"type": type(message_metadata).__name__},
            )
            message["metadata"] = {}
            message_metadata = message["metadata"]

        # ✅ SAFE payment context handling
        payment_context = message_metadata.pop("_payment_context", None)
        if payment_context is not None:
            scheduler_params["payment_context"] = payment_context

        await self.scheduler.run_task(scheduler_params)
        return task, context_id

    async def _retry_load_task(self, task_id):
        """Retry loading a task from storage."""
        retries = max(app_settings.agent.stream_missing_task_retries, 0)
        delay = max(app_settings.agent.stream_missing_task_retry_delay_seconds, 0.0)

        for _ in range(retries):
            task = await self.storage.load_task(task_id)
            if task is not None:
                return task
            await anyio.sleep(delay)

        return None

    @staticmethod
    def _to_jsonable(value: Any) -> Any:
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, dict):
            return {k: MessageHandlers._to_jsonable(v) for k, v in value.items()}
        if isinstance(value, list):
            return [MessageHandlers._to_jsonable(v) for v in value]
        return value

    @staticmethod
    def _sse_event(payload: dict[str, Any]) -> str:
        if not payload:
            return ""
        return f"data: {json.dumps(MessageHandlers._to_jsonable(payload))}\n\n"

    @trace_task_operation("send_message")
    @track_active_task
    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        task, _ = await self._submit_and_schedule_task(request["params"])
        return SendMessageResponse(jsonrpc="2.0", id=request["id"], result=task)

    @trace_task_operation("stream_message")
    @track_active_task
    async def stream_message(self, request: StreamMessageRequest):
        from starlette.responses import StreamingResponse

        task, context_id = await self._submit_and_schedule_task(request["params"])

        async def stream_generator():
            seen_status = task["status"]["state"]
            seen_artifact_ids: set[str] = set()
            cancelled_exc = anyio.get_cancelled_exc_class()
            poll_interval = max(app_settings.agent.stream_poll_interval_seconds, 0.01)

            yield self._sse_event(
                {
                    "kind": "status-update",
                    "task_id": str(task["id"]),
                    "context_id": str(context_id),
                    "status": task["status"],
                    "final": False,
                }
            )

            try:
                while True:
                    loaded_task = await self.storage.load_task(task["id"])

                    if loaded_task is None:
                        loaded_task = await self._retry_load_task(task["id"])

                    if loaded_task is None:
                        yield self._sse_event(
                            {
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
                        )
                        return

                    if "status" not in loaded_task:
                        await anyio.sleep(poll_interval)
                        continue

                    status = loaded_task["status"]["state"]

                    if status != seen_status:
                        yield self._sse_event(
                            {
                                "kind": "status-update",
                                "task_id": str(task["id"]),
                                "context_id": str(context_id),
                                "status": loaded_task["status"],
                                "final": status
                                in app_settings.agent.terminal_states,
                            }
                        )
                        seen_status = status

                    for artifact in loaded_task.get("artifacts", []):
                        artifact_id = str(artifact["artifact_id"])
                        if artifact_id in seen_artifact_ids:
                            continue

                        seen_artifact_ids.add(artifact_id)

                        yield self._sse_event(
                            {
                                "kind": "artifact-update",
                                "task_id": str(task["id"]),
                                "context_id": str(context_id),
                                "artifact": artifact,
                                "append": artifact.get("append", False),
                                "last_chunk": artifact.get("last_chunk", False),
                            }
                        )

                    if status in app_settings.agent.terminal_states:
                        return

                    await anyio.sleep(poll_interval)

            except cancelled_exc:
                logger.debug(f"Streaming client disconnected for task {task['id']}")
                return

            except Exception as e:
                logger.error(
                    "Stream processing failed",
                    extra={"task_id": str(task["id"])},
                    exc_info=True,
                )

                yield self._sse_event(
                    {
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
                )

        return StreamingResponse(
            stream_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )
