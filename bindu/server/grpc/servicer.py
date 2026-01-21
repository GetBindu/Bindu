"""gRPC servicer implementation for A2A protocol."""

from __future__ import annotations

import uuid
from typing import AsyncIterator

import grpc

from bindu.common.protocol.types import (
    SendMessageRequest,
    SendMessageResponse,
    TaskQueryParams,
    TaskIdParams,
)
from bindu.server.task_manager import TaskManager
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.grpc.servicer")

# Import converters (will work once protobuf code is generated)
try:
    from bindu.server.grpc.converters import (
        proto_to_message,
        task_to_proto,
    )
    CONVERTERS_AVAILABLE = True
except ImportError:
    CONVERTERS_AVAILABLE = False
    logger.warning("Converters not available - protobuf code needs to be generated")

# Import protobuf messages (will work once protobuf code is generated)
try:
    from bindu.grpc import a2a_pb2
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
            context.set_details("gRPC support not fully initialized. Generate protobuf code first.")
            raise NotImplementedError("gRPC support is in progress - see issue #67")

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
                "id": str(uuid.uuid4()),
            }

            # Handle configuration if present
            if request.HasField("configuration"):
                config = request.configuration
                jsonrpc_request["params"]["configuration"] = {
                    "accepted_output_modes": list(config.accepted_output_modes),
                    "long_running": config.long_running,
                }
                if config.metadata:
                    jsonrpc_request["params"]["configuration"]["metadata"] = dict(config.metadata)

            # Call TaskManager (same as JSON-RPC)
            response: SendMessageResponse = await self.task_manager.send_message(jsonrpc_request)

            # Convert Pydantic response to protobuf
            proto_response = a2a_pb2.MessageSendResponse()
            proto_response.task.CopyFrom(task_to_proto(response["result"]))

            logger.info(f"SendMessage completed: task_id={response['result']['id']}")
            return proto_response

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
        if not PROTOBUF_AVAILABLE:
            logger.error("Protobuf code not available. Cannot process StreamMessage")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("gRPC support not fully initialized.")
            raise NotImplementedError("gRPC streaming support is in progress - see issue #67")

        # TODO: Implement streaming support
        # This requires integration with the streaming mechanism
        logger.info("StreamMessage called (not yet implemented)")
        raise NotImplementedError("gRPC streaming support is in progress - see issue #67")

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
            jsonrpc_request = {
                "jsonrpc": "2.0",
                "method": "tasks/get",
                "params": TaskQueryParams(
                    task_id=request.task_id,
                ),
                "id": str(uuid.uuid4()),
            }

            # Call TaskManager
            response = await self.task_manager.get_task(jsonrpc_request)

            # Convert to protobuf
            proto_task = task_to_proto(response["result"])

            logger.info(f"GetTask completed: task_id={request.task_id}")
            return proto_task

        except Exception as e:
            logger.error(f"Error in GetTask: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details(f"Task not found: {str(e)}")
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

        try:
            # Simple health check - verify TaskManager is running
            is_healthy = self.task_manager.is_running

            proto_response = a2a_pb2.HealthCheckResponse()
            proto_response.status = (
                a2a_pb2.HealthCheckResponse.ServingStatus.SERVING
                if is_healthy
                else a2a_pb2.HealthCheckResponse.ServingStatus.NOT_SERVING
            )

            logger.info(f"HealthCheck: status={'SERVING' if is_healthy else 'NOT_SERVING'}")
            return proto_response

        except Exception as e:
            logger.error(f"Error in HealthCheck: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Health check failed: {str(e)}")
            raise

