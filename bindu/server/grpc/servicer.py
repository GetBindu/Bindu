"""gRPC servicer implementation for A2A protocol."""

from __future__ import annotations

import importlib
import json
import uuid
from typing import Any, AsyncIterator, cast

import grpc

from bindu.common.protocol.types import (
    CancelTaskRequest,
    ClearContextsRequest,
    ContextIdParams,
    DeleteTaskPushNotificationConfigRequest,
    GetTaskPushNotificationRequest,
    ListContextsRequest,
    ListTaskPushNotificationConfigRequest,
    ListTasksRequest,
    SendMessageRequest,
    SendMessageResponse,
    SetTaskPushNotificationRequest,
    StreamMessageRequest,
    TaskFeedbackRequest,
    TaskIdParams,
    TaskQueryParams,
)
from bindu.server.task_manager import TaskManager
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.grpc.servicer")

# Import converters (will work once protobuf code is generated)
try:
    from bindu.server.grpc.converters import (
        context_summary_to_proto,
        proto_to_message,
        proto_to_task_push_notification_config,
        str_to_uuid,
        task_event_to_proto,
        task_to_proto,
        task_push_notification_config_to_proto,
    )

    CONVERTERS_AVAILABLE = True
except ImportError:
    CONVERTERS_AVAILABLE = False
    logger.warning("Converters not available - protobuf code needs to be generated")

# Import protobuf messages (will work once protobuf code is generated)
a2a_pb2: Any
try:
    a2a_pb2 = importlib.import_module("bindu.grpc.a2a_pb2")
    PROTOBUF_AVAILABLE = True
except ImportError:
    a2a_pb2 = None
    PROTOBUF_AVAILABLE = False
    logger.warning("Protobuf code not generated. Run: python scripts/generate_proto.py")


class A2AServicer:
    """gRPC servicer for A2A protocol.

    This servicer implements the A2A gRPC service, converting between
    Protocol Buffer messages and Bindu's internal Pydantic models.

    Note: This class implements the methods from the generated A2AServiceServicer
    base class (in bindu.grpc.a2a_pb2_grpc). The generated base class provides
    placeholder implementations that raise NotImplementedError.

    See issue #67 for the full design: https://github.com/GetBindu/Bindu/issues/67
    """

    def __init__(self, task_manager: TaskManager):
        """Initialize A2A servicer.

        Args:
            task_manager: TaskManager instance to handle requests
        """
        self.task_manager = task_manager
        logger.info("A2AServicer initialized")

    def _map_jsonrpc_error_to_status(self, error: dict) -> grpc.StatusCode:
        """Map JSON-RPC error payloads to gRPC status codes."""
        code = error.get("code")
        message = str(error.get("message", "")).lower()

        if "identifier mismatch" in message:
            return grpc.StatusCode.FAILED_PRECONDITION
        if code == -32005:
            return grpc.StatusCode.FAILED_PRECONDITION
        if code == -32001 or "not found" in message:
            return grpc.StatusCode.NOT_FOUND
        return grpc.StatusCode.INVALID_ARGUMENT

    def _raise_on_jsonrpc_error(
        self, context: grpc.ServicerContext, response: dict
    ) -> None:
        """Raise a gRPC error if a JSON-RPC response includes an error."""
        error = response.get("error")
        if not error:
            return
        status = self._map_jsonrpc_error_to_status(error)
        message = str(error.get("message", "Unknown error"))
        context.set_code(status)
        context.set_details(message)
        raise RuntimeError(message)

    def _parse_sse_events(self, chunk: str | bytes) -> list[dict[str, Any]]:
        """Parse SSE chunk(s) into event dicts."""
        if isinstance(chunk, (bytes, bytearray)):
            text = chunk.decode("utf-8")
        else:
            text = str(chunk)

        events: list[dict[str, Any]] = []
        for line in text.splitlines():
            if not line.startswith("data:"):
                continue
            payload = line[len("data:") :].strip()
            if not payload:
                continue
            events.append(json.loads(payload))
        return events

    async def SendMessage(self, request, context):
        """Handle SendMessage gRPC call.

        Args:
            request: MessageSendRequest protobuf message
            context: gRPC context

        Returns:
            MessageSendResponse protobuf message
        """
        if not PROTOBUF_AVAILABLE or not CONVERTERS_AVAILABLE:
            logger.error("Protobuf code not available. Cannot process SendMessage")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(
                "gRPC support not fully initialized. Generate protobuf code first."
            )
            raise NotImplementedError("gRPC support is in progress - see issue #67")

        proto = cast(Any, a2a_pb2)

        try:
            # Convert protobuf request to Pydantic
            proto_message = request.message
            pydantic_message = proto_to_message(proto_message)

            # Build SendMessageRequest (JSON-RPC format)
            jsonrpc_request: SendMessageRequest = {
                "jsonrpc": "2.0",
                "method": "message/send",
                "params": {
                    "message": pydantic_message,
                    "configuration": {},
                },
                "id": uuid.uuid4(),
            }

            # Handle configuration if present
            if request.HasField("configuration"):
                config = request.configuration
                jsonrpc_request["params"]["configuration"] = {
                    "accepted_output_modes": list(config.accepted_output_modes),
                    "long_running": config.long_running,
                }
                if config.metadata:
                    jsonrpc_request["params"]["configuration"]["metadata"] = dict(
                        config.metadata
                    )

            # Call TaskManager (same as JSON-RPC)
            response: SendMessageResponse = await self.task_manager.send_message(
                jsonrpc_request
            )
            self._raise_on_jsonrpc_error(context, response)

            # Convert Pydantic response to protobuf
            proto_response = proto.MessageSendResponse()
            proto_response.task.CopyFrom(task_to_proto(response["result"]))

            logger.info(f"SendMessage completed: task_id={response['result']['id']}")
            return proto_response

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Error in SendMessage: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            raise

    async def StreamMessage(self, request, context) -> AsyncIterator:
        """Handle StreamMessage gRPC call with bidirectional streaming.

        Args:
            request: MessageSendRequest protobuf message
            context: gRPC context

        Yields:
            TaskEvent protobuf messages
        """
        if not PROTOBUF_AVAILABLE or not CONVERTERS_AVAILABLE:
            logger.error("Protobuf code not available. Cannot process StreamMessage")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("gRPC support not fully initialized.")
            raise NotImplementedError(
                "gRPC streaming support is in progress - see issue #67"
            )
        try:
            proto_message = request.message
            pydantic_message = proto_to_message(proto_message)

            jsonrpc_request: StreamMessageRequest = {
                "jsonrpc": "2.0",
                "method": "message/stream",
                "params": {
                    "message": pydantic_message,
                    "configuration": {},
                },
                "id": uuid.uuid4(),
            }

            if request.HasField("configuration"):
                config = request.configuration
                jsonrpc_request["params"]["configuration"] = {
                    "accepted_output_modes": list(config.accepted_output_modes),
                    "long_running": config.long_running,
                }
                if config.metadata:
                    jsonrpc_request["params"]["configuration"]["metadata"] = dict(
                        config.metadata
                    )

            stream_response = await self.task_manager.stream_message(jsonrpc_request)
            body_iterator = getattr(stream_response, "body_iterator", None)
            if body_iterator is None:
                context.set_code(grpc.StatusCode.INTERNAL)
                context.set_details("Streaming response not available.")
                raise RuntimeError("Streaming response not available.")

            async for chunk in body_iterator:
                for event in self._parse_sse_events(chunk):
                    yield task_event_to_proto(event)

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Error in StreamMessage: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            raise

    async def GetTask(self, request, context):
        """Handle GetTask gRPC call.

        Args:
            request: TaskQueryRequest protobuf message
            context: gRPC context

        Returns:
            Task protobuf message
        """
        if not PROTOBUF_AVAILABLE or not CONVERTERS_AVAILABLE:
            logger.error("Protobuf code not available. Cannot process GetTask")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("gRPC support not fully initialized.")
            raise NotImplementedError("gRPC support is in progress - see issue #67")

        try:
            # Build TaskQueryParams (JSON-RPC format)
            task_id = str_to_uuid(request.task_id)
            if task_id is None:
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Invalid task_id")
                raise RuntimeError("Invalid task_id")
            jsonrpc_request = {
                "jsonrpc": "2.0",
                "method": "tasks/get",
                "params": TaskQueryParams(
                    task_id=task_id,
                ),
                "id": uuid.uuid4(),
            }

            # Call TaskManager
            response = await self.task_manager.get_task(jsonrpc_request)
            self._raise_on_jsonrpc_error(context, response)

            # Convert to protobuf
            proto_task = task_to_proto(response["result"])

            logger.info(f"GetTask completed: task_id={request.task_id}")
            return proto_task

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Error in GetTask: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Task not found: {str(e)}")
            raise

    async def ListTasks(self, request, context):
        """Handle ListTasks gRPC call."""
        if not PROTOBUF_AVAILABLE or not CONVERTERS_AVAILABLE:
            logger.error("Protobuf code not available. Cannot process ListTasks")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("gRPC support not fully initialized.")
            raise NotImplementedError("gRPC support is in progress - see issue #67")

        proto = cast(Any, a2a_pb2)

        try:
            params: dict[str, Any] = {}
            if request.limit:
                params["length"] = request.limit

            jsonrpc_request = cast(
                ListTasksRequest,
                {
                    "jsonrpc": "2.0",
                    "method": "tasks/list",
                    "params": params,
                    "id": uuid.uuid4(),
                },
            )

            response = await self.task_manager.list_tasks(jsonrpc_request)
            self._raise_on_jsonrpc_error(context, response)

            proto_response = proto.TaskListResponse()
            tasks = response.get("result") or []
            for task in tasks:
                proto_response.tasks.append(task_to_proto(task))
            return proto_response

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Error in ListTasks: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            raise

    async def CancelTask(self, request, context):
        """Handle CancelTask gRPC call."""
        if not PROTOBUF_AVAILABLE or not CONVERTERS_AVAILABLE:
            logger.error("Protobuf code not available. Cannot process CancelTask")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("gRPC support not fully initialized.")
            raise NotImplementedError("gRPC support is in progress - see issue #67")

        try:
            task_id = str_to_uuid(request.task_id) or uuid.UUID(int=0)
            jsonrpc_request: CancelTaskRequest = {
                "jsonrpc": "2.0",
                "method": "tasks/cancel",
                "params": TaskIdParams(task_id=task_id),
                "id": uuid.uuid4(),
            }

            response = await self.task_manager.cancel_task(jsonrpc_request)
            self._raise_on_jsonrpc_error(context, response)

            return task_to_proto(response["result"])

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Error in CancelTask: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            raise

    async def TaskFeedback(self, request, context):
        """Handle TaskFeedback gRPC call."""
        if not PROTOBUF_AVAILABLE or not CONVERTERS_AVAILABLE:
            logger.error("Protobuf code not available. Cannot process TaskFeedback")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("gRPC support not fully initialized.")
            raise NotImplementedError("gRPC support is in progress - see issue #67")

        proto = cast(Any, a2a_pb2)

        try:
            task_id = str_to_uuid(request.task_id) or uuid.UUID(int=0)
            params: dict[str, Any] = {
                "task_id": task_id,
                "feedback": request.feedback,
            }
            if request.rating:
                params["rating"] = request.rating
            if request.metadata:
                params["metadata"] = dict(request.metadata)

            jsonrpc_request: TaskFeedbackRequest = {
                "jsonrpc": "2.0",
                "method": "tasks/feedback",
                "params": params,
                "id": uuid.uuid4(),
            }

            response = await self.task_manager.task_feedback(jsonrpc_request)
            self._raise_on_jsonrpc_error(context, response)

            result = response.get("result") or {}
            proto_response = proto.TaskFeedbackResponse()
            proto_response.success = True
            proto_response.message = str(result.get("message", "Feedback submitted"))
            return proto_response

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Error in TaskFeedback: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            raise

    async def ListContexts(self, request, context):
        """Handle ListContexts gRPC call."""
        if not PROTOBUF_AVAILABLE or not CONVERTERS_AVAILABLE:
            logger.error("Protobuf code not available. Cannot process ListContexts")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("gRPC support not fully initialized.")
            raise NotImplementedError("gRPC support is in progress - see issue #67")

        proto = cast(Any, a2a_pb2)

        try:
            params: dict[str, Any] = {}
            if request.limit:
                params["length"] = request.limit

            jsonrpc_request = cast(
                ListContextsRequest,
                {
                    "jsonrpc": "2.0",
                    "method": "contexts/list",
                    "params": params,
                    "id": uuid.uuid4(),
                },
            )

            response = await self.task_manager.list_contexts(jsonrpc_request)
            self._raise_on_jsonrpc_error(context, response)

            proto_response = proto.ContextListResponse()
            contexts = response.get("result") or []
            for context_summary in contexts:
                proto_response.contexts.append(
                    context_summary_to_proto(context_summary)
                )
            return proto_response

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Error in ListContexts: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            raise

    async def ClearContext(self, request, context):
        """Handle ClearContext gRPC call."""
        if not PROTOBUF_AVAILABLE or not CONVERTERS_AVAILABLE:
            logger.error("Protobuf code not available. Cannot process ClearContext")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("gRPC support not fully initialized.")
            raise NotImplementedError("gRPC support is in progress - see issue #67")

        proto = cast(Any, a2a_pb2)

        try:
            context_id = str_to_uuid(request.context_id) or uuid.UUID(int=0)
            jsonrpc_request: ClearContextsRequest = {
                "jsonrpc": "2.0",
                "method": "contexts/clear",
                "params": ContextIdParams(context_id=context_id),
                "id": uuid.uuid4(),
            }

            response = await self.task_manager.clear_context(jsonrpc_request)
            self._raise_on_jsonrpc_error(context, response)

            result = response.get("result") or {}
            proto_response = proto.ContextClearResponse()
            proto_response.success = True
            proto_response.message = str(result.get("message", "Context cleared"))
            return proto_response

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Error in ClearContext: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            raise

    async def SetTaskPushNotification(self, request, context):
        """Handle SetTaskPushNotification gRPC call."""
        if not PROTOBUF_AVAILABLE or not CONVERTERS_AVAILABLE:
            logger.error(
                "Protobuf code not available. Cannot process SetTaskPushNotification"
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("gRPC support not fully initialized.")
            raise NotImplementedError("gRPC support is in progress - see issue #67")

        try:
            pydantic_config = proto_to_task_push_notification_config(request.config)
            jsonrpc_request: SetTaskPushNotificationRequest = {
                "jsonrpc": "2.0",
                "method": "tasks/pushNotification/set",
                "params": pydantic_config,
                "id": uuid.uuid4(),
            }

            response = await self.task_manager.set_task_push_notification(
                jsonrpc_request
            )
            self._raise_on_jsonrpc_error(context, response)

            proto_response = task_push_notification_config_to_proto(response["result"])
            return proto_response

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Error in SetTaskPushNotification: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            raise

    async def GetTaskPushNotification(self, request, context):
        """Handle GetTaskPushNotification gRPC call."""
        if not PROTOBUF_AVAILABLE or not CONVERTERS_AVAILABLE:
            logger.error(
                "Protobuf code not available. Cannot process GetTaskPushNotification"
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("gRPC support not fully initialized.")
            raise NotImplementedError("gRPC support is in progress - see issue #67")

        try:
            task_id = str_to_uuid(request.task_id) or uuid.UUID(int=0)
            jsonrpc_request: GetTaskPushNotificationRequest = {
                "jsonrpc": "2.0",
                "method": "tasks/pushNotification/get",
                "params": TaskIdParams(task_id=task_id),
                "id": uuid.uuid4(),
            }

            response = await self.task_manager.get_task_push_notification(
                jsonrpc_request
            )
            self._raise_on_jsonrpc_error(context, response)

            proto_response = task_push_notification_config_to_proto(response["result"])
            return proto_response

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Error in GetTaskPushNotification: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            raise

    async def ListTaskPushNotifications(self, request, context):
        """Handle ListTaskPushNotifications gRPC call."""
        if not PROTOBUF_AVAILABLE or not CONVERTERS_AVAILABLE:
            logger.error(
                "Protobuf code not available. Cannot process ListTaskPushNotifications"
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("gRPC support not fully initialized.")
            raise NotImplementedError("gRPC support is in progress - see issue #67")

        proto = cast(Any, a2a_pb2)

        try:
            task_id = str_to_uuid(request.id) or uuid.UUID(int=0)
            jsonrpc_request: ListTaskPushNotificationConfigRequest = {
                "jsonrpc": "2.0",
                "method": "tasks/pushNotificationConfig/list",
                "params": {
                    "id": task_id,
                },
                "id": uuid.uuid4(),
            }

            response = await self.task_manager.list_task_push_notifications(
                jsonrpc_request
            )
            self._raise_on_jsonrpc_error(context, response)

            proto_response = proto.TaskPushNotificationListResponse()
            proto_response.configs.append(
                task_push_notification_config_to_proto(response["result"])
            )
            return proto_response

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Error in ListTaskPushNotifications: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            raise

    async def DeleteTaskPushNotification(self, request, context):
        """Handle DeleteTaskPushNotification gRPC call."""
        if not PROTOBUF_AVAILABLE or not CONVERTERS_AVAILABLE:
            logger.error(
                "Protobuf code not available. Cannot process DeleteTaskPushNotification"
            )
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("gRPC support not fully initialized.")
            raise NotImplementedError("gRPC support is in progress - see issue #67")

        proto = cast(Any, a2a_pb2)

        try:
            task_id = str_to_uuid(request.id) or uuid.UUID(int=0)
            config_id = str_to_uuid(request.push_notification_config_id) or uuid.UUID(
                int=0
            )
            jsonrpc_request: DeleteTaskPushNotificationConfigRequest = {
                "jsonrpc": "2.0",
                "method": "tasks/pushNotificationConfig/delete",
                "params": {
                    "id": task_id,
                    "push_notification_config_id": config_id,
                },
                "id": uuid.uuid4(),
            }

            response = await self.task_manager.delete_task_push_notification(
                jsonrpc_request
            )
            self._raise_on_jsonrpc_error(context, response)

            proto_response = proto.DeleteTaskPushNotificationResponse()
            proto_response.config.CopyFrom(
                task_push_notification_config_to_proto(response["result"])
            )
            return proto_response

        except RuntimeError:
            raise
        except Exception as e:
            logger.error(f"Error in DeleteTaskPushNotification: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            raise

    async def HealthCheck(self, request, context):
        """Handle HealthCheck gRPC call.

        Args:
            request: HealthCheckRequest protobuf message
            context: gRPC context

        Returns:
            HealthCheckResponse protobuf message
        """
        if not PROTOBUF_AVAILABLE:
            # Return error if protobuf not available
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("gRPC support not fully initialized.")
            raise NotImplementedError("gRPC support is in progress - see issue #67")

        proto = cast(Any, a2a_pb2)

        try:
            # Simple health check - verify TaskManager is running
            is_healthy = self.task_manager.is_running

            proto_response = proto.HealthCheckResponse()
            proto_response.status = (
                proto.HealthCheckResponse.ServingStatus.SERVING
                if is_healthy
                else proto.HealthCheckResponse.ServingStatus.NOT_SERVING
            )

            logger.info(
                f"HealthCheck: status={'SERVING' if is_healthy else 'NOT_SERVING'}"
            )
            return proto_response

        except Exception as e:
            logger.error(f"Error in HealthCheck: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Health check failed: {str(e)}")
            raise
