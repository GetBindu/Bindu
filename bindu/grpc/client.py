"""gRPC client for calling remote agent handlers.

GrpcAgentClient is a callable class that replaces manifest.run for agents
registered via gRPC. When ManifestWorker calls manifest.run(messages) at
line 171 of manifest_worker.py, this client makes a gRPC call to the SDK's
AgentHandler endpoint and returns the result in the same format that
ResultProcessor and ResponseDetector expect.

Supports both unary and streaming responses:
    - Unary (HandleMessages): Returns str or dict directly.
    - Streaming (HandleMessagesStream): Returns a generator that yields
      chunks. ResultProcessor.collect_results() drains it automatically.

Key contract:
    - Input:  list[dict[str, str]] — chat messages [{"role": "user", "content": "..."}]
    - Output: str (normal completion), dict with "state" key (state transition),
      or generator of str/dict (streaming — collected by ResultProcessor).

This means ManifestWorker, ResultProcessor, and ResponseDetector require
zero changes — they cannot tell the difference between a local Python handler
and a remote gRPC handler.
"""

from __future__ import annotations

from typing import Any

import grpc

from bindu.grpc.generated import agent_handler_pb2, agent_handler_pb2_grpc
from bindu.utils.logging import get_logger

logger = get_logger("bindu.grpc.client")


class GrpcAgentClient:
    """Callable gRPC client that acts as manifest.run for remote agents.

    When the Bindu core registers a remote agent (via BinduService.RegisterAgent),
    it creates a GrpcAgentClient pointing to the SDK's AgentHandler server.
    This client is set as manifest.run, so ManifestWorker calls it transparently.

    Supports both unary and streaming modes:
        - Unary: Calls HandleMessages, returns str or dict.
        - Streaming: Calls HandleMessagesStream, returns a generator.
          ResultProcessor.collect_results() handles generators via __next__.

    The __call__ signature uses 'messages' as the parameter name to pass
    validate_agent_function() inspection.

    Attributes:
        _address: The SDK's AgentHandler gRPC address (e.g., "localhost:50052").
        _timeout: Timeout in seconds for HandleMessages calls.
        _use_streaming: Whether to use HandleMessagesStream instead of HandleMessages.
        _channel: Lazy-initialized gRPC channel.
        _stub: Lazy-initialized AgentHandler stub.
    """

    def __init__(
        self,
        callback_address: str,
        timeout: float = 30.0,
        use_streaming: bool = False,
    ) -> None:
        """Initialize the gRPC agent client.

        Args:
            callback_address: The SDK's AgentHandler gRPC server address
                (e.g., "localhost:50052").
            timeout: Timeout in seconds for HandleMessages calls.
            use_streaming: If True, use HandleMessagesStream (server-side streaming)
                instead of HandleMessages (unary). The streaming RPC returns a
                generator that ResultProcessor.collect_results() will drain.
        """
        self._address = callback_address
        self._timeout = timeout
        self._use_streaming = use_streaming
        self._channel: grpc.Channel | None = None
        self._stub: agent_handler_pb2_grpc.AgentHandlerStub | None = None

    def _ensure_connected(self) -> None:
        """Lazily create the gRPC channel and stub on first use."""
        if self._channel is None:
            self._channel = grpc.insecure_channel(
                self._address,
                options=[
                    ("grpc.max_receive_message_length", 4 * 1024 * 1024),
                    ("grpc.max_send_message_length", 4 * 1024 * 1024),
                ],
            )
            self._stub = agent_handler_pb2_grpc.AgentHandlerStub(self._channel)
            logger.debug(f"Connected to agent handler at {self._address}")

    def _build_request(
        self, messages: list[dict[str, str]]
    ) -> agent_handler_pb2.HandleRequest:
        """Convert chat-format messages to a proto HandleRequest.

        Args:
            messages: Conversation history as list of dicts.
                Each dict has "role" (str) and "content" (str) keys.

        Returns:
            HandleRequest proto message ready for gRPC call.
        """
        proto_messages = [
            agent_handler_pb2.ChatMessage(
                role=m.get("role", "user"),
                content=m.get("content", ""),
            )
            for m in messages
        ]
        return agent_handler_pb2.HandleRequest(messages=proto_messages)

    def __call__(self, messages: list[dict[str, str]], **kwargs: Any) -> Any:
        """Execute the remote handler with conversation history.

        Called by ManifestWorker at line 171:
            raw_results = self.manifest.run(message_history or [])

        Supports two modes:
            - Unary (default): Calls HandleMessages, returns str or dict.
            - Streaming: Calls HandleMessagesStream, returns a generator.
              ResultProcessor.collect_results() drains generators via __next__.

        Args:
            messages: Conversation history as list of dicts.
                Each dict has "role" (str) and "content" (str) keys.
            **kwargs: Additional keyword arguments (ignored, for compatibility).

        Returns:
            Unary mode:
                str: Plain text response (maps to "completed" task state).
                dict: Structured response with "state" key for state transitions.
            Streaming mode:
                Generator[str | dict]: Yields chunks. ResultProcessor.collect_results()
                uses the last yielded value as the final result.

        Raises:
            grpc.RpcError: If the gRPC call fails (caught by ManifestWorker's
                try/except which calls _handle_task_failure).
        """
        self._ensure_connected()
        assert self._stub is not None

        request = self._build_request(messages)

        if self._use_streaming:
            logger.debug(
                f"Calling HandleMessagesStream on {self._address} "
                f"with {len(request.messages)} messages"
            )
            return self._handle_streaming(request)
        else:
            logger.debug(
                f"Calling HandleMessages on {self._address} "
                f"with {len(request.messages)} messages"
            )
            return self._handle_unary(request)

    def _handle_unary(
        self, request: agent_handler_pb2.HandleRequest
    ) -> str | dict[str, Any]:
        """Make a unary HandleMessages call.

        Args:
            request: Proto HandleRequest.

        Returns:
            str or dict from _response_to_result().
        """
        assert self._stub is not None
        response = self._stub.HandleMessages(request, timeout=self._timeout)
        return self._response_to_result(response)

    def _handle_streaming(self, request: agent_handler_pb2.HandleRequest) -> Any:
        """Make a streaming HandleMessagesStream call.

        Returns a generator that yields results from the stream.
        ResultProcessor.collect_results() detects this via __next__
        and drains it, using the last yielded value as the final result.

        Args:
            request: Proto HandleRequest.

        Yields:
            str or dict from _response_to_result() for each stream chunk.
        """
        assert self._stub is not None
        response_stream = self._stub.HandleMessagesStream(
            request, timeout=self._timeout
        )
        for response in response_stream:
            yield self._response_to_result(response)

    @staticmethod
    def _response_to_result(
        response: agent_handler_pb2.HandleResponse,
    ) -> str | dict[str, Any]:
        """Convert a proto HandleResponse to the format ResultProcessor expects.

        The downstream processing chain expects:
        - str: Normal text response → task completes
        - dict with "state" key: State transition → task stays open
            e.g., {"state": "input-required", "prompt": "Can you clarify?"}

        Args:
            response: Proto HandleResponse from the SDK.

        Returns:
            str or dict matching what ResponseDetector.determine_task_state() expects.
        """
        if response.state:
            # Structured response — maps to intermediate task state
            result: dict[str, Any] = {"state": response.state}
            if response.prompt:
                result["prompt"] = response.prompt
            if response.content:
                result["content"] = response.content
            # Include any extra metadata from the SDK
            for key, value in response.metadata.items():
                result[key] = value
            return result
        else:
            # Plain string response — maps to "completed" task state
            return response.content

    def health_check(self) -> bool:
        """Check if the remote SDK agent is healthy.

        Returns:
            True if the agent responds and reports healthy, False otherwise.
        """
        self._ensure_connected()
        assert self._stub is not None
        try:
            response = self._stub.HealthCheck(
                agent_handler_pb2.HealthCheckRequest(),
                timeout=5.0,
            )
            return response.healthy
        except grpc.RpcError as e:
            logger.warning(f"Health check failed for {self._address}: {e}")
            return False

    def get_capabilities(
        self,
    ) -> agent_handler_pb2.GetCapabilitiesResponse | None:
        """Query the remote SDK agent's capabilities.

        Returns:
            GetCapabilitiesResponse if successful, None on failure.
        """
        self._ensure_connected()
        assert self._stub is not None
        try:
            return self._stub.GetCapabilities(
                agent_handler_pb2.GetCapabilitiesRequest(),
                timeout=5.0,
            )
        except grpc.RpcError as e:
            logger.warning(f"GetCapabilities failed for {self._address}: {e}")
            return None

    def close(self) -> None:
        """Close the gRPC channel and release resources."""
        if self._channel is not None:
            self._channel.close()
            self._channel = None
            self._stub = None
            logger.debug(f"Closed connection to {self._address}")

    def __repr__(self) -> str:  # noqa: D105
        mode = "streaming" if self._use_streaming else "unary"
        return (
            f"GrpcAgentClient(address={self._address!r}, "
            f"timeout={self._timeout}, mode={mode})"
        )
