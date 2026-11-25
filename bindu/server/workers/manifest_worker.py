"""ManifestWorker implementation for executing tasks using AgentManifest.

Hybrid Agent Architecture (A2A Protocol):
    This worker implements a hybrid agent pattern where:

    1. Messages for Interaction (Task Open):
       - Agent responds with Messages during task execution
       - Task remains in 'working', 'input-required', or 'auth-required' state
       - No artifacts generated yet

    2. Artifacts for Completion (Task Terminal):
       - Agent responds with Artifacts when task completes
       - Task moves to 'completed' state (terminal)
       - Final deliverable is stored as artifact

    Example Flow:
        Context1
          └─ Task1 (state: working)
              ├─ Input1 → LLM → Output1 (Message, state: input-required)
              ├─ Input2 → LLM → Output2 (Message + Artifact, state: completed)

    A2A Protocol Compliance:
    - Tasks are immutable once terminal (completed/failed/canceled)
    - Refinements create NEW tasks with same contextId
    - referenceTaskIds link related tasks
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from uuid import UUID

import anyio

from opentelemetry.trace import Status, StatusCode, get_current_span, get_tracer
from x402.http import FacilitatorConfig, HTTPFacilitatorClient

from bindu.settings import app_settings

from bindu.common.protocol.types import (
    Artifact,
    Message,
    Task,
    TaskIdParams,
    TaskSendParams,
    TaskState,
)
from bindu.penguin.manifest import AgentManifest
from bindu.server.workers.base import Worker
from bindu.server.workers.helpers import ResponseDetector, ResultProcessor
from bindu.utils.logging import get_logger
from bindu.utils.retry import TRANSIENT_EXCEPTIONS, retry_worker_operation
from bindu.utils.worker import ArtifactBuilder, MessageConverter, TaskStateManager

tracer = get_tracer("bindu.server.workers.manifest_worker")
logger = get_logger("bindu.server.workers.manifest_worker")

# Constants
TASK_NOT_FOUND_ERROR = "Task {task_id} not found"

# Bound on the shielded orphan-payment metadata write: a storage row held by
# another transaction must not be able to stall worker shutdown forever.
ORPHAN_TAG_TIMEOUT_SECONDS = 5.0

# Bound on the shielded settle-time receipt persist, for the same reason;
# on timeout the run proceeds and later writes re-attach the receipt.
RECEIPT_PERSIST_TIMEOUT_SECONDS = 5.0
INVALID_TERMINAL_STATE_ERROR = (
    "Invalid terminal state '{state}'. Must be one of: {terminal_states}"
)


def _jsonable_copy(value: Any) -> Any:
    """Structurally copy containers, stringifying UUID leaves.

    Handler input must be (a) isolated — the in-memory backend's
    list_tasks_by_context hands out live references to stored task dicts,
    so without copying nested containers a handler mutating `parts` would
    corrupt stored history — and (b) JSON-serializable with the same shape
    on every storage backend (memory preserves UUID objects, Postgres loads
    them differently). Leaf values (including large base64 payload strings)
    are shared, not duplicated.
    """
    if isinstance(value, dict):
        return {k: _jsonable_copy(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable_copy(v) for v in value]
    if isinstance(value, UUID):
        return str(value)
    return value


@dataclass
class ManifestWorker(Worker):
    """Concrete worker implementation using AgentManifest for task execution.

    This worker wraps an AgentManifest and implements the hybrid agent pattern,
    handling state transitions, message generation, and artifact creation.

    Hybrid Pattern Implementation:
    - Detects agent response type (input-required, auth-required, or complete)
    - Returns Messages for interaction (task stays open)
    - Returns Artifacts for completion (task becomes immutable)

    Structured Response Support:
    - Parses JSON responses: {"state": "input-required", "prompt": "..."}
    - Falls back to heuristic detection for backward compatibility
    - Extracts metadata (auth_type, service) when available

    A2A Protocol Compliance:
    - Uses referenceTaskIds for conversation history
    - Maintains context continuity across tasks
    - Ensures task immutability after terminal states
    """

    manifest: AgentManifest
    """The agent manifest containing execution logic and DID identity."""

    lifecycle_notifier: Optional[Callable[[UUID, UUID, str, bool], Any]] = field(
        default=None
    )
    """Optional callback for task lifecycle notifications (task_id, context_id, state, final)."""

    @retry_worker_operation()
    async def run_task(self, params: TaskSendParams) -> None:
        """Execute a task using the AgentManifest.

        Hybrid Pattern Flow:
        1. Load task and validate state
        2. Build conversation history (using referenceTaskIds or context)
        3. Execute manifest with conversation context
        4. Detect response type:
           - input-required → Message only, task stays open
           - auth-required → Message only, task stays open
           - normal → Message + Artifact, task completes
        5. Update storage with appropriate state and content
        6. Settle payment if task completes successfully (x402 flow)

        Args:
            params: Task execution parameters containing task_id, context_id, message,
                   and optional payment_context from middleware

        Raises:
            ValueError: If task not found
            Exception: Re-raised after marking task as failed
        """
        # Step 1: Load and validate task
        task = await self.storage.load_task(params["task_id"])
        if task is None:
            raise ValueError(TASK_NOT_FOUND_ERROR.format(task_id=params["task_id"]))

        # A cancel can now land while the run is still queued behind the
        # concurrency gates. Skip silently — validate_task_state would raise
        # and the failure guard would overwrite 'canceled' with 'failed'.
        if task["status"]["state"] == "canceled":
            logger.info(
                f"Task {task['id']} canceled before execution started; skipping"
            )
            return

        # Extract payment context if available (from x402 middleware)
        payment_context = params.get("payment_context")

        await TaskStateManager.validate_task_state(task)

        # Settle BEFORE doing any work (settle-first ordering).
        #
        # Rationale: x402 `/verify` is a probabilistic check, not a reservation —
        # the payer's balance can change between verify and settle, and parallel
        # nonces from the same wallet can pass verify independently. If we settle
        # only after the LLM call, every failed settle costs the agent the LLM
        # bill. Settling first means a failed settle has zero LLM cost.
        #
        # Google A2A's x402 extension takes the same approach for long-running
        # tasks; the latency is dominated by the LLM call anyway, so happy-path
        # wall-clock is unchanged.
        settlement_metadata: dict[str, Any] | None = None
        if payment_context:
            # Shielded: a cancel landing mid-settle must not leave moved
            # money known only to this coroutine's locals. The facilitator
            # call is bounded by its own HTTP timeout; once it returns, the
            # receipt is persisted on the task BEFORE any cancellation point,
            # so an interrupted run can never drop a settled payment's
            # reconciliation data.
            with anyio.CancelScope(shield=True):
                settlement_metadata = await self._settle_payment(payment_context)
                settled_ok = (
                    settlement_metadata.get(app_settings.x402.meta_status_key)
                    == app_settings.x402.status_completed
                )
                if settled_ok:
                    # Receipt durability: persist before any cancellation
                    # point. Bounded — this write runs shielded, and a
                    # contended storage row must not stall worker shutdown
                    # behind the shield — and best-effort: on timeout or
                    # failure the paid run still proceeds (aborting would
                    # guarantee an orphan), and every later terminal/orphan
                    # write re-attaches the receipt from
                    # settlement_metadata. Settlement is never repeated.
                    try:
                        with anyio.fail_after(RECEIPT_PERSIST_TIMEOUT_SECONDS):
                            await self.storage.update_task(
                                task["id"], metadata=settlement_metadata
                            )
                    except Exception as e:  # noqa: BLE001 - best-effort upfront persist
                        logger.warning(
                            f"Could not persist settlement receipt for task "
                            f"{task['id']} upfront: {e}; continuing — later "
                            "writes re-attach it"
                        )
            if not settled_ok:
                # No state transition to "working", no LLM call — just record
                # the failure and exit. Reconciliation metadata is already in
                # settlement_metadata (nonce, authorization, network).
                await self._handle_settlement_failure(task, settlement_metadata)
                return

        # Everything after settlement runs inside the try so the
        # cancellation handler below covers EVERY post-settlement
        # checkpoint — the working update, the lifecycle notification, and
        # the history build, not just handler execution. A cancel deferred
        # by the shielded settle block above is delivered at the first of
        # these awaits, and a paid run interrupted there must still be
        # tagged as orphaned. pre_handler_phase keeps transient
        # infrastructure errors in this region retryable (see the
        # exception handler below).
        pre_handler_phase = True
        try:
            # Add span event for state transition
            self._add_state_change_event(to_state="working")

            # Transition to working — guarded: only from 'submitted'. A
            # cancel can CAS the task away between the queued-state check
            # above and here; the guard makes this write lose that race
            # instead of resurrecting the task (any settled receipt is
            # already persisted).
            updated = await self.storage.update_task(
                task["id"], state="working", expected_states=("submitted",)
            )
            if updated is None:
                # A cancel won between the queued-state check and here. If
                # the payment already settled (shielded block above), record
                # the orphan — money moved, nothing will be produced.
                if settlement_metadata:
                    await self._record_orphaned_payment(task["id"], settlement_metadata)
                logger.info(
                    f"Task {task['id']} left 'submitted' before execution; skipping run"
                )
                return
            await self._notify_lifecycle(
                task["id"], task["context_id"], "working", False
            )

            # Step 2: Build conversation history (A2A Protocol)
            message_history = await self._build_complete_message_history(task)
            pre_handler_phase = False

            # Step 3: Execute manifest with system prompt (if enabled)
            if (
                self.manifest.enable_system_message
                and app_settings.agent.enable_structured_responses
            ):
                # Inject structured response system prompt as first message.
                # A2A-shaped like the rest of the history — handlers see one
                # uniform contract (every message has `parts`), and the gRPC
                # boundary maps role "system" through unchanged via ROLE_MAP.
                system_prompt = app_settings.agent.structured_response_system_prompt
                if system_prompt:
                    system_message = {
                        "role": "system",
                        "kind": "message",
                        "parts": [{"kind": "text", "text": system_prompt}],
                    }
                    # Create new list to avoid mutating original message_history
                    message_history = [system_message] + (message_history or [])

            # Step 3.1: Execute agent with tracing
            with tracer.start_as_current_span("agent.execute") as agent_span:
                start_time = time.time()

                # Set agent-specific attributes
                agent_span.set_attributes(
                    {
                        "bindu.agent.name": self.manifest.name,
                        "bindu.agent.did": str(self.manifest.did_extension.did),
                        "bindu.agent.message_count": len(message_history or []),
                        "bindu.component": "agent_execution",
                    }
                )

                try:
                    # Type narrowing: manifest.run should be callable
                    assert self.manifest.run is not None
                    # Pass message history as structured list of dicts
                    raw_results = self.manifest.run(message_history or [])

                    # Handle generator/async generator responses
                    collected_results = await ResultProcessor.collect_results(
                        raw_results
                    )

                    # Normalize result to extract final response (intelligent extraction)
                    results = ResultProcessor.normalize_result(collected_results)

                    # Record successful execution
                    execution_time = time.time() - start_time
                    agent_span.set_attribute(
                        "bindu.agent.execution_time", execution_time
                    )
                    agent_span.set_status(Status(StatusCode.OK))

                except Exception as agent_error:
                    # Record agent execution failure
                    execution_time = time.time() - start_time
                    agent_span.set_attributes(
                        {
                            "bindu.agent.execution_time": execution_time,
                            "bindu.agent.error_type": type(agent_error).__name__,
                            "bindu.agent.error_message": str(agent_error),
                        }
                    )
                    agent_span.set_status(Status(StatusCode.ERROR, str(agent_error)))
                    raise

            # Step 4: Parse response and detect state
            structured_response = ResponseDetector.parse_structured_response(results)

            # Determine task state based on response
            state, message_content = ResponseDetector.determine_task_state(
                results, structured_response
            )

            if state in ("input-required", "auth-required"):
                # Hybrid Pattern: Return Message only, keep task open
                # Add span event for state transition
                self._add_state_change_event(from_state="working", to_state=state)
                await self._handle_intermediate_state(
                    task, state, message_content, settlement_metadata
                )
            else:
                # Hybrid Pattern: Task complete - generate Message + Artifacts
                # Add span event for state transition
                self._add_state_change_event(from_state="working", to_state=state)
                await self._handle_terminal_state(
                    task, results, state, settlement_metadata=settlement_metadata
                )

        except anyio.get_cancelled_exc_class():
            # tasks/cancel (or shutdown) interrupted the run. If the payer
            # was already debited (settle-first), re-tag the persisted
            # receipt so operators can find canceled-but-paid tasks for
            # reconciliation — money moved, no artifact was delivered. The
            # helper's guard keeps an interrupt that lands AFTER the
            # completion write committed (e.g. during the notification
            # awaits) from re-tagging a task whose deliverable exists.
            if settlement_metadata:
                await self._record_orphaned_payment(task["id"], settlement_metadata)
            raise
        except Exception as e:
            if (
                pre_handler_phase
                and settlement_metadata is None
                and isinstance(e, TRANSIENT_EXCEPTIONS)
            ):
                # A retryable infrastructure error before any handler work
                # on an UNPAID run: re-raise untouched so the retry
                # decorator re-runs the task while it is still 'submitted'
                # — a failure write here would make the retry a no-op (the
                # working guard would reject it). Paid runs are excluded:
                # re-running would re-enter settlement, and a second settle
                # of the same nonce fails, so the failure path below
                # (which records the orphan) is the safer outcome.
                raise
            # Handle task failure with error message
            # Add span event for failure
            self._add_state_change_event(
                from_state="working", to_state="failed", error=str(e)
            )
            # If we already debited the payer (settle-first succeeded), the work
            # failure is an "orphan payment" — money moved, no artifact delivered.
            # x402 has no native refund; persist enough metadata for an operator
            # to issue a manual transfer back.
            await self._handle_task_failure(
                task, str(e), settlement_metadata=settlement_metadata
            )
            raise
        return

    @retry_worker_operation(max_attempts=2)
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a task — and actually stop its in-flight execution.

        Interrupting the run comes FIRST, unconditionally: the API handler
        (task_handlers.cancel_task) CAS-flips the task to 'canceled' before
        signaling the scheduler, so by the time this operation arrives the
        storage row usually already reads 'canceled' — the provider call it
        is paying for is still running until the scope here is cancelled.

        Args:
            params: Task identification parameters containing task_id
        """
        task = await self.storage.load_task(params["task_id"])
        if not task:
            return

        interrupted = self._cancel_in_flight(params["task_id"])
        if interrupted:
            logger.info(f"Task {task['id']} execution interrupted by cancel")

        current_state = task["status"]["state"]
        if current_state == "canceled":
            # The API handler already claimed the state transition; this
            # operation still owed the interrupt above and the lifecycle
            # notification below.
            await self._notify_lifecycle(
                params["task_id"], task["context_id"], "canceled", True
            )
            return

        if current_state in app_settings.agent.terminal_states:
            # completed/failed/rejected: immutable per A2A, nothing ran.
            logger.debug(
                f"Task {task['id']} already terminal ({current_state}); cancel ignored"
            )
            return

        # Direct scheduler-path cancel (no API CAS): record and notify.
        # Guarded — if another writer made the task terminal between the
        # load above and this write, that transition wins (and notified).
        self._add_state_change_event(from_state=current_state, to_state="canceled")
        updated = await self.storage.update_task(
            params["task_id"],
            state="canceled",
            expected_states=app_settings.agent.non_terminal_states,
        )
        if updated is None:
            return
        await self._notify_lifecycle(
            params["task_id"], task["context_id"], "canceled", True
        )

    def build_message_history(self, history: list[Message]) -> list[dict[str, Any]]:
        """Pass A2A protocol messages through — each keeps its ``parts``.

        Handlers read ``messages[-1]["parts"]`` (text / file / data parts)
        directly; that is the A2A contract agents are written against. Do NOT
        flatten to ``{role, content}`` here: it discards ``parts``, and the
        file interceptor cannot represent binary (PDF/image) bytes as text,
        so every file/vision handler receives an empty message. Chat-format
        flattening happens only at the gRPC boundary
        (``GrpcAgentClient._build_request``), whose proto requires it.

        Messages are structurally copied (see ``_jsonable_copy``) so handler
        mutations cannot reach stored task history, and envelope UUIDs are
        stringified so the input is JSON-serializable and shaped identically
        on every storage backend. ``parts`` content is untouched.

        Args:
            history: List of A2A protocol Message objects

        Returns:
            The same messages as plain JSON-safe dicts, ``parts`` intact.
        """
        return [_jsonable_copy(m) for m in history]

    def build_artifacts(self, result: Any) -> list[Artifact]:
        """Convert manifest execution result to A2A protocol artifacts.

        Args:
            result: Agent execution result (any format)

        Returns:
            List of Artifact objects with DID signature

        Note:
            Only called when task completes (hybrid pattern)
        """
        did_extension = self.manifest.did_extension
        return ArtifactBuilder.from_result(result, did_extension=did_extension)

    async def _build_complete_message_history(self, task: Task) -> list[dict[str, Any]]:
        """Build complete conversation history following A2A Protocol.

        A2A Protocol Strategy:
        1. If referenceTaskIds present: Build from referenced tasks (explicit)
        2. Otherwise: Build from all tasks in context (implicit)

        This enables:
        - Task refinements with explicit references
        - Parallel task execution within same context
        - Conversation continuity across multiple tasks

        Args:
            task: Current task being executed

        Returns:
            List of A2A protocol messages (``parts`` intact) for agent execution
        """
        # Extract referenceTaskIds from current task message
        current_message = task.get("history", [])[0] if task.get("history") else None
        reference_task_ids: list = []

        if current_message and "reference_task_ids" in current_message:
            reference_task_ids = current_message["reference_task_ids"]

        if reference_task_ids:
            # Strategy 1: Explicit references (A2A refinement pattern)
            referenced_messages: list[Message] = []
            for task_id in reference_task_ids:
                # Ensure task_id is UUID object
                task_id_uuid = UUID(task_id) if isinstance(task_id, str) else task_id
                ref_task = await self.storage.load_task(task_id_uuid)
                if ref_task and ref_task.get("history"):
                    referenced_messages.extend(ref_task["history"])

            current_messages = task.get("history", [])
            all_messages = referenced_messages + current_messages

        elif self.manifest.enable_context_based_history:
            # Strategy 2: Context-based history (implicit continuation)
            # Only enabled if configured in manifest
            tasks_by_context = await self.storage.list_tasks_by_context(
                task["context_id"]
            )
            previous_tasks = [t for t in tasks_by_context if t["id"] != task["id"]]

            all_previous_messages: list[Message] = []
            for prev_task in previous_tasks:
                history = prev_task.get("history", [])
                if history:
                    all_previous_messages.extend(history)

            current_messages = task.get("history", [])
            all_messages = all_previous_messages + current_messages
        else:
            # No context-based history - only use current task messages
            all_messages = task.get("history", [])

        return self.build_message_history(all_messages) if all_messages else []

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _add_state_change_event(
        self,
        to_state: str,
        from_state: str | None = None,
        error: str | None = None,
    ) -> None:
        """Add state change event to current OpenTelemetry span.

        Args:
            to_state: Target state
            from_state: Optional source state
            error: Optional error message
        """
        current_span = get_current_span()
        if current_span.is_recording():
            attributes: dict[str, str] = {"to_state": to_state}
            if from_state:
                attributes["from_state"] = from_state
            if error:
                attributes["error"] = error
            current_span.add_event("task.state_changed", attributes=attributes)

    def _log_notification_error(
        self,
        notification_type: str,
        task_id: UUID,
        context_id: UUID,
        error: Exception,
        **extra_context: Any,
    ) -> None:
        """Log notification delivery errors.

        Args:
            notification_type: Type of notification (e.g., 'Lifecycle', 'Artifact')
            task_id: Task identifier
            context_id: Context identifier
            error: Exception that occurred
            **extra_context: Additional context to log
        """
        # ERROR + traceback rather than a one-line WARNING. A failed
        # notification is user-impacting (the operator's inbox never
        # receives the artifact or state transition) and silent
        # str(error) hides the call site — see the agno RunResponse →
        # DataPart serialization bug that vanished here for weeks.
        logger.opt(exception=error).error(
            f"{notification_type} notification failed",
            task_id=str(task_id),
            context_id=str(context_id),
            error=str(error),
            error_type=type(error).__name__,
            **extra_context,
        )

    # -------------------------------------------------------------------------
    # Message Normalization
    # -------------------------------------------------------------------------

    async def _handle_intermediate_state(
        self,
        task: Task,
        state: TaskState,
        message_content: Any,
        settlement_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Handle intermediate task states (input-required, auth-required).

        A2A Protocol Compliance:
        - Agent messages are added to task.history
        - Task remains in mutable state (working, input-required, auth-required)
        - All information is in the message, no redundant metadata

        Args:
            task: Current task
            state: Task state to set
            message_content: Content for agent message (any type: str, dict, list, etc.)
            settlement_metadata: Pre-settled payment metadata, if the run was
                paid — used to record an orphan when the guarded write loses
                to a cancel and the prompt is discarded
        """
        # Render message content for user; for structured, prefer 'prompt' field
        content = (
            message_content.get("prompt")
            if isinstance(message_content, dict) and message_content.get("prompt")
            else message_content
        )
        agent_messages = MessageConverter.to_protocol_messages(
            content, task["id"], task["context_id"]
        )

        # Re-attach the settlement receipt (idempotent merge): if the
        # bounded upfront persist failed, this committed write is the
        # recovery point for a paid run that pauses on input/auth —
        # otherwise the receipt would exist only in run_task's locals
        # once the run returns.
        metadata: dict[str, Any] | None = (
            dict(settlement_metadata) if settlement_metadata else None
        )

        # Update task with state and append agent messages to history.
        # Guarded: a cancel that landed mid-run must not be overwritten by
        # a late input-required/auth-required transition.
        updated = await self.storage.update_task(
            task["id"],
            state=state,
            new_messages=agent_messages,
            metadata=metadata,
            expected_states=("working",),
        )
        if updated is None:
            # A cancel won the race: the prompt is discarded, so a paid run
            # delivered nothing — record the orphan (a committed intermediate
            # prompt never reaches this branch and keeps payment-completed).
            if settlement_metadata:
                await self._record_orphaned_payment(task["id"], settlement_metadata)
            logger.info(
                f"Task {task['id']} no longer 'working'; {state} update discarded"
            )
            return
        # Forward the rendered prompt to the operator inbox via the
        # lifecycle webhook. Coerce to a string conservatively — if the
        # handler returned a structured value without a "prompt" key,
        # `content` is still that raw value here.
        status_message = content if isinstance(content, str) else None
        await self._notify_lifecycle(
            task["id"], task["context_id"], state, False, status_message
        )

    async def _handle_terminal_state(
        self,
        task: Task,
        results: Any,
        state: TaskState = "completed",
        additional_metadata: dict[str, Any] | None = None,
        settlement_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Handle terminal task states (completed/failed).

        Hybrid Pattern - Terminal States:
        - completed: Message (explanation) + Artifacts (deliverable)
        - failed: Message (error explanation) only, NO artifacts
        - canceled: State change only, NO new content

        A2A Protocol Compliance:
        - Agent messages are added to task.history
        - Artifacts are added to task.artifacts (completed only)
        - Task becomes immutable after reaching terminal state

        X402 Payment Flow:
        - Settlement happens upfront in run_task (settle-first), so by the time
          we get here the payer has already been debited. We just attach the
          settlement metadata (receipts) to the task.

        Args:
            task: Task dict being finalized
            results: Agent execution results
            state: Terminal state (completed or failed)
            additional_metadata: Optional metadata to attach to task
            settlement_metadata: Pre-settled payment metadata from run_task

        Raises:
            ValueError: If state is not a terminal state
        """
        # Validate that state is terminal
        if state not in app_settings.agent.terminal_states:
            raise ValueError(
                INVALID_TERMINAL_STATE_ERROR.format(
                    state=state, terminal_states=app_settings.agent.terminal_states
                )
            )

        # Handle different terminal states
        if state == "completed":
            # Success: Add both Message and Artifacts
            agent_messages = MessageConverter.to_protocol_messages(
                results, task["id"], task["context_id"]
            )
            artifacts = self.build_artifacts(results)

            # Attach pre-settled payment metadata (receipts, tx hash) to the task.
            # Settlement itself happened upfront in run_task; if it had failed we
            # would not be in the "completed" branch.
            if settlement_metadata:
                if additional_metadata:
                    additional_metadata.update(settlement_metadata)
                else:
                    additional_metadata = settlement_metadata

            # Persist task state BEFORE sending any notifications (outbox pattern).
            # If a notification fires before the DB write and then the process crashes,
            # clients receive an artifact webhook but the task is still "working" in the
            # DB — an inconsistent state.  Write first, then notify.
            #
            # Guarded ('working' only): if a cancel won the race while the
            # handler was finishing, the task is already terminal — per A2A
            # immutability the late result is discarded, with no artifact or
            # completion notifications. A settled payment receipt was
            # persisted at settle time, so nothing is lost with it.
            updated = await self.storage.update_task(
                task["id"],
                state=state,
                new_artifacts=artifacts,
                new_messages=agent_messages,
                metadata=additional_metadata,
                expected_states=("working",),
            )
            if updated is None:
                # A cancel won the race (e.g. the scheduler interrupt never
                # reached this worker): the late result is discarded with no
                # artifacts committed, so a settled payment is an orphan —
                # money moved, nothing delivered.
                if settlement_metadata:
                    await self._record_orphaned_payment(task["id"], settlement_metadata)
                logger.info(
                    f"Task {task['id']} already terminal; completed result discarded"
                )
                return

            # Send artifact notifications after the DB is committed
            for artifact in artifacts:
                await self._notify_artifact(task["id"], task["context_id"], artifact)

            await self._notify_lifecycle(task["id"], task["context_id"], state, True)

        elif state in ("failed", "rejected"):
            # Failure/Rejection: Message only (explanation), NO artifacts
            error_message = MessageConverter.to_protocol_messages(
                results, task["id"], task["context_id"]
            )
            updated = await self.storage.update_task(
                task["id"],
                state=state,
                new_messages=error_message,
                metadata=additional_metadata,
                expected_states=("working",),
            )
            if updated is None:
                logger.info(
                    f"Task {task['id']} already terminal; {state} result discarded"
                )
                return
            await self._notify_lifecycle(task["id"], task["context_id"], state, True)

        elif state == "canceled":
            # Canceled: State change only, NO new content
            updated = await self.storage.update_task(
                task["id"],
                state=state,
                expected_states=app_settings.agent.non_terminal_states,
            )
            if updated is None:
                return
            await self._notify_lifecycle(task["id"], task["context_id"], state, True)

    async def _handle_settlement_failure(
        self, task: Task, settlement_metadata: dict[str, Any]
    ) -> None:
        """Mark task failed because settle-first rejected the payment.

        Called from run_task BEFORE the task transitions to "working" — so
        no LLM call ran, no artifact was generated, nothing to withhold.
        ``settlement_metadata`` carries the recovery fields (nonce,
        authorization, network) for operator visibility.

        The user-facing message is intentionally generic — the facilitator's
        raw error string (which can disclose internal infra detail) stays in
        ``task.metadata[x402.payment.error]`` for the operator, not on the
        wire to the caller.
        """
        error_message = MessageConverter.to_protocol_messages(
            "Payment settlement failed; task not executed.",
            task["id"],
            task["context_id"],
        )
        self._add_state_change_event(
            from_state="submitted", to_state="failed", error="settlement_failed"
        )
        # Guarded: settle-first runs before the working transition, so this
        # write only lands while the task is still 'submitted'. If a cancel
        # got there first, nothing moved (the settle failed) — skip.
        updated = await self.storage.update_task(
            task["id"],
            state="failed",
            new_messages=error_message,
            metadata=settlement_metadata,
            expected_states=("submitted",),
        )
        if updated is None:
            logger.info(
                f"Task {task['id']} no longer 'submitted'; settlement failure not recorded"
            )
            return
        await self._notify_lifecycle(task["id"], task["context_id"], "failed", True)

    async def _handle_task_failure(
        self,
        task: Task,
        error: str,
        settlement_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Handle task execution failure.

        Creates an error message and marks task as failed without artifacts.

        A2A Protocol Compliance:
        - Error message added to task.history
        - Task marked as failed (terminal state)

        X402 Orphan-Payment Handling:
        - Under settle-first, work failure happens AFTER the payer has been
          debited on-chain. We cannot auto-refund (x402 has no refund
          primitive), so we flag the payment as ``payment-orphaned`` and
          persist the EIP-3009 fields so an operator can issue a manual
          transfer back to the payer.

        Args:
            task: Task that failed
            error: Error description
            settlement_metadata: Pre-settled payment metadata, if present
        """
        error_message = MessageConverter.to_protocol_messages(
            f"Task execution failed: {error}", task["id"], task["context_id"]
        )
        metadata: dict[str, Any] | None = None
        if settlement_metadata:
            # Re-tag the status — the payment itself succeeded, but the work
            # didn't, so this is a refund-required state, not a settlement
            # failure. The receipts and EIP-3009 fields stay intact.
            metadata = {
                **settlement_metadata,
                app_settings.x402.meta_status_key: "payment-orphaned",
            }
        updated = await self.storage.update_task(
            task["id"],
            state="failed",
            new_messages=error_message,
            metadata=metadata,
            expected_states=app_settings.agent.non_terminal_states,
        )
        if updated is None:
            # The task went terminal (canceled) while failing. Keep the
            # orphan-payment reconciliation data without touching the state.
            if settlement_metadata:
                await self._record_orphaned_payment(task["id"], settlement_metadata)
            return
        await self._notify_lifecycle(task["id"], task["context_id"], "failed", True)

    async def _record_orphaned_payment(
        self, task_id: UUID, settlement_metadata: dict[str, Any]
    ) -> None:
        """Tag a settled payment whose run ended without a committed deliverable.

        Shielded, so an in-flight cancellation cannot drop the
        reconciliation record, and bounded, so a contended storage row
        cannot stall shutdown behind the shield. The guarded write excludes
        exactly 'completed' — the one state that proves a deliverable was
        committed — so a late interrupt never re-tags a delivered task,
        while canceled and independently failed paid runs (e.g. a stream
        error marked the task failed before the worker's own write) stay
        reconcilable. Best-effort: on timeout or storage failure the task
        still carries its settle-time receipt; only the orphan re-tag is
        lost, and the loss is logged for the operator.
        """
        allowed = tuple(app_settings.agent.non_terminal_states) + (
            "canceled",
            "failed",
            "rejected",
        )
        try:
            with anyio.CancelScope(shield=True):
                with anyio.fail_after(ORPHAN_TAG_TIMEOUT_SECONDS):
                    await self.storage.update_task(
                        task_id,
                        metadata={
                            **settlement_metadata,
                            app_settings.x402.meta_status_key: "payment-orphaned",
                        },
                        expected_states=allowed,
                    )
        except Exception as e:  # noqa: BLE001 - best-effort reconciliation tag
            logger.error(
                f"Could not record orphaned payment for task {task_id}: {e}; "
                "the settle-time receipt usually remains on the task, but its "
                "bounded write is best-effort too — if both writes failed, "
                "this log line is the reconciliation record: "
                f"{settlement_metadata}"
            )

    async def _settle_payment(self, payment_context: dict[str, Any]) -> dict[str, Any]:
        """Settle payment after successful task completion.

        This method is called only when a task completes successfully with payment context.
        It calls the facilitator to settle the payment and returns metadata to attach to the task.

        Args:
            payment_context: Payment details from x402 middleware containing:
                - payment_payload: The payment payload from the client
                - payment_requirements: The payment requirements for this agent
                - verify_response: The verification response from facilitator

        Returns:
            Metadata dict containing settlement information to attach to task
        """
        # Pull the EIP-3009 fields out of the raw dict up front so they end
        # up in every failure return path. Validation or facilitator errors
        # otherwise strip the nonce/authorization, and we lose any chance to
        # reconcile a half-settled transaction later (issue #562).
        payment_payload_dict = payment_context.get("payment_payload", {}) or {}
        scheme_payload = payment_payload_dict.get("payload", {}) or {}
        authorization = scheme_payload.get("authorization", {}) or {}
        nonce = authorization.get("nonce")
        network = payment_payload_dict.get("network")

        def _failure_metadata(reason: str) -> dict[str, Any]:
            md: dict[str, Any] = {
                app_settings.x402.meta_status_key: app_settings.x402.status_failed,
                app_settings.x402.meta_error_key: reason,
            }
            if nonce is not None:
                md["x402_nonce"] = nonce
            if authorization:
                md["x402_authorization"] = authorization
            if network is not None:
                md["x402_network"] = network
            return md

        try:
            from x402 import PaymentPayload, PaymentRequirements

            payment_requirements_dict = payment_context["payment_requirements"]

            # Convert dicts back to Pydantic models (they were serialized in a2a_protocol)
            payment_payload = PaymentPayload.model_validate(payment_payload_dict)
            payment_requirements = PaymentRequirements.model_validate(
                payment_requirements_dict
            )

            # Initialize a fresh facilitator client per settlement. The
            # ResourceServer that holds a long-lived client for verify
            # lives on the application instance and is not in scope here.
            facilitator = HTTPFacilitatorClient(
                FacilitatorConfig(url=app_settings.x402.facilitator_url)
            )

            # Settle payment
            logger.info("Settling payment for completed task")
            settle_response = await facilitator.settle(
                payment_payload, payment_requirements
            )

            if settle_response.success:
                logger.info("Payment settled successfully")
                return {
                    app_settings.x402.meta_status_key: app_settings.x402.status_completed,
                    app_settings.x402.meta_receipts_key: [settle_response.model_dump()],
                }
            else:
                error_reason = settle_response.error_reason or "Unknown error"
                # loguru parses braces in the message template; values that may
                # contain JSON (`{...}`) — facilitator errors do — must go
                # through positional placeholders, not f-string interpolation.
                logger.error("Payment settlement failed: {}", error_reason)
                return _failure_metadata(error_reason)

        except Exception as e:
            # Same reason as above — exception strings from the x402 SDK
            # routinely embed the failing JSON body, which trips loguru's
            # template parser if we use an f-string here.
            logger.opt(exception=True).error("Error settling payment: {}", e)
            return _failure_metadata(str(e))

    async def _notify_artifact(
        self, task_id: UUID, context_id: UUID, artifact: Artifact
    ) -> None:
        """Notify about artifact generation if push manager is available.

        Args:
            task_id: Task identifier
            context_id: Context identifier
            artifact: The artifact that was generated
        """
        if self.lifecycle_notifier:
            try:
                # Get push manager from lifecycle_notifier's bound instance
                push_manager = getattr(self.lifecycle_notifier, "__self__", None)
                if push_manager and hasattr(push_manager, "notify_artifact"):
                    result = push_manager.notify_artifact(task_id, context_id, artifact)
                    if hasattr(result, "__await__"):
                        await result
            except Exception as e:
                # Log but don't disrupt task execution on notification errors
                self._log_notification_error("Artifact", task_id, context_id, e)

    async def _notify_lifecycle(
        self,
        task_id: UUID,
        context_id: UUID,
        state: str,
        final: bool,
        status_message: str | None = None,
    ) -> None:
        """Notify lifecycle changes if notifier is configured.

        Args:
            task_id: Task identifier
            context_id: Context identifier
            state: New task state
            final: Whether this is a terminal state
            status_message: Optional human-readable text for non-terminal
                states (e.g., the agent's prompt for input-required).
                Operator inboxes render this so the user can see what the
                agent is waiting on instead of just "state changed".
        """
        if self.lifecycle_notifier:
            try:
                # Pass status_message only when supported by the notifier's
                # signature — keeps third-party notifiers (which may still
                # have the 4-arg shape) working.
                try:
                    result = self.lifecycle_notifier(
                        task_id,
                        context_id,
                        state,
                        final,
                        status_message,  # ty: ignore[too-many-positional-arguments]
                    )
                except TypeError:
                    result = self.lifecycle_notifier(task_id, context_id, state, final)
                # Handle both sync and async notifiers
                if hasattr(result, "__await__"):
                    await result
            except Exception as e:
                # Log but don't disrupt task execution on notification errors
                self._log_notification_error(
                    "Lifecycle", task_id, context_id, e, state=state
                )
