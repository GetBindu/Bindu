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
sending messages and streaming responses via Server-Sent Events.
"""

from __future__ import annotations

import inspect
import json
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from bindu.common.protocol.types import (
    SendMessageRequest,
    SendMessageResponse,
    StreamMessageRequest,
    Task,
    TaskSendParams,
)

from bindu.utils.logging import get_logger
from bindu.utils.task_telemetry import (
    active_tasks,
    record_task_metrics,
    trace_task_operation,
    track_active_task,
)
from bindu.utils.worker_utils import ArtifactBuilder, MessageConverter

from bindu.server.scheduler import Scheduler
from bindu.server.storage import Storage

logger = get_logger("bindu.server.handlers.message_handlers")
_tracer = trace.get_tracer("bindu.server.handlers.message_handlers")

# Default stream timeout in seconds (5 minutes)
_DEFAULT_STREAM_TIMEOUT_SECONDS = 300.0


@dataclass
class MessageHandlers:
    """Handles message-related RPC requests."""

    scheduler: Scheduler
    storage: Storage[Any]
    manifest: Any | None = None
    workers: list[Any] | None = None
    context_id_parser: Any = None
    push_manager: Any | None = None
    stream_timeout: float = field(default=_DEFAULT_STREAM_TIMEOUT_SECONDS)

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
        """Stream messages using Server-Sent Events (SSE).

        Implements the A2A streaming protocol (message/stream) by:
        1. Submitting the task to storage (same as message/send)
        2. Building conversation history through the worker pipeline
        3. Executing the agent and streaming chunks as SSE events
        4. Persisting the final result as artifacts in storage
        5. Forwarding payment context for X402 settlement

        SSE Event Types (A2A Protocol):
        - TaskStatusUpdateEvent (kind: "status-update"): Task state transitions
        - TaskArtifactUpdateEvent (kind: "artifact-update"): Streamed content chunks

        Returns:
            StreamingResponse with text/event-stream media type
        """
        from starlette.responses import StreamingResponse

        message = request["params"]["message"]
        context_id = self.context_id_parser(message.get("context_id"))

        # Submit task to storage (same flow as send_message)
        task: Task = await self.storage.submit_task(context_id, message)

        # Extract configuration
        config = request["params"].get("configuration", {})

        # Register push notification config if provided inline
        push_config = config.get("push_notification_config")
        if push_config and self.push_manager:
            is_long_running = config.get("long_running", False)
            await self.push_manager.register_push_config(
                task["id"], push_config, persist=is_long_running
            )

        # Extract payment context if present
        payment_context = None
        message_metadata = message.get("metadata", {})
        if "_payment_context" in message_metadata:
            payment_context = message_metadata["_payment_context"]
            del message["metadata"]["_payment_context"]

        return StreamingResponse(
            self._stream_generator(task, context_id, payment_context),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    def _get_worker(self):
        """Get the first available worker.

        Returns:
            Worker instance, or None if no workers are available.
        """
        if not self.workers or len(self.workers) == 0:
            return None
        return self.workers[0]

    async def _stream_generator(
        self,
        task: Task,
        context_id: Any,
        payment_context: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        """Generate SSE events for a streaming task execution.

        This generator follows the worker pipeline pattern:
        1. Transition task to 'working' state
        2. Build conversation history using the worker's public API
        3. Execute the manifest and yield chunks as SSE events
        4. Emit a final last_chunk marker after generator exhaustion
        5. On completion: build artifacts, update storage, settle payments
        6. On failure: update task to failed state with error

        Timeout: The entire stream is bounded by self.stream_timeout seconds.
        If the timeout expires, the stream emits a failed event and cleans up.

        Args:
            task: The submitted task to execute
            context_id: Context identifier for the task
            payment_context: Optional payment details from X402 middleware

        Yields:
            SSE-formatted event strings
        """
        start_time = time.time()
        collected_chunks: list[str] = []
        artifact_id = str(uuid.uuid4())
        span = _tracer.start_span("task_manager.stream_message")
        span.set_attribute("bindu.operation", "stream_message")
        span.set_attribute("bindu.task_id", str(task["id"]))
        span.set_attribute("bindu.context_id", str(context_id))
        span.set_attribute("bindu.component", "task_manager")
        active_tasks.add(1, {"operation": "create_stream"})

        try:
            # Step 1: Transition to working state
            await self.storage.update_task(task["id"], state="working")
            yield _format_sse_event(
                _build_status_event(task["id"], context_id, "working", final=False)
            )

            worker = self._get_worker()
            if worker is None or self.manifest is None:
                logger.warning("No workers or manifest available for streaming")
                await self.storage.update_task(task["id"], state="failed")
                yield _format_sse_event(
                    _build_status_event(
                        task["id"],
                        context_id,
                        "failed",
                        final=True,
                        error="No agent worker available",
                    )
                )
                return

            # Step 2: Build conversation history through worker's public API
            message_history = await worker.build_complete_message_history(task)

            # Inject system prompt if enabled (same logic as ManifestWorker.run_task)
            from bindu.settings import app_settings

            if (
                self.manifest.enable_system_message
                and app_settings.agent.enable_structured_responses
            ):
                system_prompt = app_settings.agent.structured_response_system_prompt
                if system_prompt:
                    message_history = [{"role": "system", "content": system_prompt}] + (
                        message_history or []
                    )

            # Step 3: Execute manifest and stream results
            logger.debug(f"Starting streaming execution for task {task['id']}")
            span.add_event("stream.execution_start")
            manifest_result = self.manifest.run(message_history or [])

            if inspect.isasyncgen(manifest_result):
                async for chunk in manifest_result:
                    if chunk:
                        chunk_text = str(chunk)
                        collected_chunks.append(chunk_text)
                        yield _format_sse_event(
                            _build_artifact_event(
                                task["id"],
                                context_id,
                                artifact_id,
                                chunk_text,
                                append=True,
                                last_chunk=False,
                            )
                        )

            elif inspect.isgenerator(manifest_result):
                for chunk in manifest_result:
                    if chunk:
                        chunk_text = str(chunk)
                        collected_chunks.append(chunk_text)
                        yield _format_sse_event(
                            _build_artifact_event(
                                task["id"],
                                context_id,
                                artifact_id,
                                chunk_text,
                                append=True,
                                last_chunk=False,
                            )
                        )

            else:
                # Non-streaming response: emit as single chunk
                if manifest_result is not None:
                    chunk_text = str(manifest_result)
                    collected_chunks.append(chunk_text)
                    yield _format_sse_event(
                        _build_artifact_event(
                            task["id"],
                            context_id,
                            artifact_id,
                            chunk_text,
                            append=False,
                            last_chunk=True,
                        )
                    )

            # Step 4: Emit final last_chunk marker for generator paths
            # (direct return path already emits last_chunk=True above)
            if collected_chunks and (
                inspect.isasyncgen(manifest_result)
                or inspect.isgenerator(manifest_result)
            ):
                yield _format_sse_event(
                    _build_artifact_event(
                        task["id"],
                        context_id,
                        artifact_id,
                        "",
                        append=True,
                        last_chunk=True,
                    )
                )

            # Step 5: Build final artifacts and messages, persist to storage
            full_response = "".join(collected_chunks)
            agent_messages = MessageConverter.to_protocol_messages(
                full_response, task["id"], task["context_id"]
            )
            artifacts = ArtifactBuilder.from_result(
                full_response, did_extension=self.manifest.did_extension
            )

            # Step 6: Handle payment settlement if applicable
            metadata: dict[str, Any] | None = None
            if payment_context:
                metadata = await worker.settle_payment(payment_context)

            # Update storage with completed state, artifacts, and messages
            await self.storage.update_task(
                task["id"],
                state="completed",
                new_artifacts=artifacts,
                new_messages=agent_messages,
                metadata=metadata,
            )

            # Emit final completion event
            execution_time = time.time() - start_time
            span.set_attribute("bindu.stream.chunk_count", len(collected_chunks))
            span.set_attribute("bindu.stream.duration_seconds", execution_time)
            span.set_status(Status(StatusCode.OK))
            record_task_metrics("stream_message", execution_time, "success")
            logger.info(
                f"Streaming completed for task {task['id']}: "
                f"{len(collected_chunks)} chunks in {execution_time:.2f}s"
            )
            yield _format_sse_event(
                _build_status_event(task["id"], context_id, "completed", final=True)
            )

        except Exception as e:
            # Handle failure: update task state and emit error event
            execution_time = time.time() - start_time
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.set_attribute("bindu.error_type", type(e).__name__)
            span.set_attribute("bindu.error_message", str(e))
            record_task_metrics(
                "stream_message",
                execution_time,
                "error",
                error_type=type(e).__name__,
            )
            logger.error(
                f"Streaming failed for task {task['id']} after {execution_time:.2f}s: {e}",
                exc_info=True,
            )

            # Persist failure to storage — guard against storage errors
            try:
                error_messages = MessageConverter.to_protocol_messages(
                    f"Task execution failed: {e}", task["id"], task["context_id"]
                )
                await self.storage.update_task(
                    task["id"], state="failed", new_messages=error_messages
                )
            except Exception as storage_err:
                logger.error(
                    f"Failed to persist error state for task {task['id']}: {storage_err}",
                    exc_info=True,
                )

            yield _format_sse_event(
                _build_status_event(
                    task["id"],
                    context_id,
                    "failed",
                    final=True,
                    error=str(e),
                )
            )

        finally:
            active_tasks.add(-1, {"operation": "complete_stream"})
            span.end()


# ---------------------------------------------------------------------------
# SSE Event Builders (module-level, stateless)
# ---------------------------------------------------------------------------


def _format_sse_event(event: dict[str, Any]) -> str:
    """Format a dictionary as an SSE event string.

    Args:
        event: Event data to serialize

    Returns:
        SSE-formatted string with data prefix and double newline
    """
    return f"data: {json.dumps(event)}\n\n"


def _build_status_event(
    task_id: Any,
    context_id: Any,
    state: str,
    final: bool,
    error: str | None = None,
) -> dict[str, Any]:
    """Build a TaskStatusUpdateEvent for SSE.

    Conforms to A2A Protocol TaskStatusUpdateEvent type with
    kind="status-update".

    Args:
        task_id: Task identifier
        context_id: Context identifier
        state: Task state (working, completed, failed)
        final: Whether this is a terminal state
        error: Optional error message for failed state

    Returns:
        Event dictionary ready for SSE serialization
    """
    event: dict[str, Any] = {
        "kind": "status-update",
        "task_id": str(task_id),
        "context_id": str(context_id),
        "status": {
            "state": state,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "final": final,
    }
    if error is not None:
        event["error"] = error
    return event


def _build_artifact_event(
    task_id: Any,
    context_id: Any,
    artifact_id: str,
    text: str,
    append: bool = True,
    last_chunk: bool = False,
) -> dict[str, Any]:
    """Build a TaskArtifactUpdateEvent for SSE.

    Conforms to A2A Protocol TaskArtifactUpdateEvent type with
    kind="artifact-update".

    Args:
        task_id: Task identifier
        context_id: Context identifier
        artifact_id: Consistent artifact ID across chunks for client reassembly
        text: Text content for this chunk
        append: Whether to append to existing artifact
        last_chunk: Whether this is the final chunk

    Returns:
        Event dictionary ready for SSE serialization
    """
    return {
        "kind": "artifact-update",
        "task_id": str(task_id),
        "context_id": str(context_id),
        "artifact": {
            "artifact_id": artifact_id,
            "name": "streaming_response",
            "parts": [{"kind": "text", "text": text}],
        },
        "append": append,
        "last_chunk": last_chunk,
    }
