from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class RegisterAgentRequest(_message.Message):
    __slots__ = ("config_json", "skills", "grpc_callback_address")
    CONFIG_JSON_FIELD_NUMBER: _ClassVar[int]
    SKILLS_FIELD_NUMBER: _ClassVar[int]
    GRPC_CALLBACK_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    config_json: str
    skills: _containers.RepeatedCompositeFieldContainer[SkillDefinition]
    grpc_callback_address: str
    def __init__(
        self,
        config_json: _Optional[str] = ...,
        skills: _Optional[_Iterable[_Union[SkillDefinition, _Mapping]]] = ...,
        grpc_callback_address: _Optional[str] = ...,
    ) -> None: ...

class RegisterAgentResponse(_message.Message):
    __slots__ = ("success", "agent_id", "did", "agent_url", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    DID_FIELD_NUMBER: _ClassVar[int]
    AGENT_URL_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    agent_id: str
    did: str
    agent_url: str
    error: str
    def __init__(
        self,
        success: bool = ...,
        agent_id: _Optional[str] = ...,
        did: _Optional[str] = ...,
        agent_url: _Optional[str] = ...,
        error: _Optional[str] = ...,
    ) -> None: ...

class HeartbeatRequest(_message.Message):
    __slots__ = ("agent_id", "timestamp")
    AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    agent_id: str
    timestamp: int
    def __init__(
        self, agent_id: _Optional[str] = ..., timestamp: _Optional[int] = ...
    ) -> None: ...

class HeartbeatResponse(_message.Message):
    __slots__ = ("acknowledged", "server_timestamp")
    ACKNOWLEDGED_FIELD_NUMBER: _ClassVar[int]
    SERVER_TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    acknowledged: bool
    server_timestamp: int
    def __init__(
        self, acknowledged: bool = ..., server_timestamp: _Optional[int] = ...
    ) -> None: ...

class UnregisterAgentRequest(_message.Message):
    __slots__ = ("agent_id",)
    AGENT_ID_FIELD_NUMBER: _ClassVar[int]
    agent_id: str
    def __init__(self, agent_id: _Optional[str] = ...) -> None: ...

class UnregisterAgentResponse(_message.Message):
    __slots__ = ("success", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    error: str
    def __init__(self, success: bool = ..., error: _Optional[str] = ...) -> None: ...

class ChatMessage(_message.Message):
    __slots__ = ("role", "content")
    ROLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    role: str
    content: str
    def __init__(
        self, role: _Optional[str] = ..., content: _Optional[str] = ...
    ) -> None: ...

class HandleRequest(_message.Message):
    __slots__ = ("messages", "task_id", "context_id")
    MESSAGES_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    messages: _containers.RepeatedCompositeFieldContainer[ChatMessage]
    task_id: str
    context_id: str
    def __init__(
        self,
        messages: _Optional[_Iterable[_Union[ChatMessage, _Mapping]]] = ...,
        task_id: _Optional[str] = ...,
        context_id: _Optional[str] = ...,
    ) -> None: ...

class HandleResponse(_message.Message):
    __slots__ = ("content", "state", "prompt", "is_final", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[str] = ...
        ) -> None: ...

    CONTENT_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    PROMPT_FIELD_NUMBER: _ClassVar[int]
    IS_FINAL_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    content: str
    state: str
    prompt: str
    is_final: bool
    metadata: _containers.ScalarMap[str, str]
    def __init__(
        self,
        content: _Optional[str] = ...,
        state: _Optional[str] = ...,
        prompt: _Optional[str] = ...,
        is_final: bool = ...,
        metadata: _Optional[_Mapping[str, str]] = ...,
    ) -> None: ...

class SkillDefinition(_message.Message):
    __slots__ = (
        "name",
        "description",
        "tags",
        "input_modes",
        "output_modes",
        "version",
        "author",
        "raw_content",
        "format",
    )
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    INPUT_MODES_FIELD_NUMBER: _ClassVar[int]
    OUTPUT_MODES_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    AUTHOR_FIELD_NUMBER: _ClassVar[int]
    RAW_CONTENT_FIELD_NUMBER: _ClassVar[int]
    FORMAT_FIELD_NUMBER: _ClassVar[int]
    name: str
    description: str
    tags: _containers.RepeatedScalarFieldContainer[str]
    input_modes: _containers.RepeatedScalarFieldContainer[str]
    output_modes: _containers.RepeatedScalarFieldContainer[str]
    version: str
    author: str
    raw_content: str
    format: str
    def __init__(
        self,
        name: _Optional[str] = ...,
        description: _Optional[str] = ...,
        tags: _Optional[_Iterable[str]] = ...,
        input_modes: _Optional[_Iterable[str]] = ...,
        output_modes: _Optional[_Iterable[str]] = ...,
        version: _Optional[str] = ...,
        author: _Optional[str] = ...,
        raw_content: _Optional[str] = ...,
        format: _Optional[str] = ...,
    ) -> None: ...

class GetCapabilitiesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetCapabilitiesResponse(_message.Message):
    __slots__ = ("name", "description", "version", "supports_streaming", "skills")
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    SUPPORTS_STREAMING_FIELD_NUMBER: _ClassVar[int]
    SKILLS_FIELD_NUMBER: _ClassVar[int]
    name: str
    description: str
    version: str
    supports_streaming: bool
    skills: _containers.RepeatedCompositeFieldContainer[SkillDefinition]
    def __init__(
        self,
        name: _Optional[str] = ...,
        description: _Optional[str] = ...,
        version: _Optional[str] = ...,
        supports_streaming: bool = ...,
        skills: _Optional[_Iterable[_Union[SkillDefinition, _Mapping]]] = ...,
    ) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("healthy", "message")
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    message: str
    def __init__(self, healthy: bool = ..., message: _Optional[str] = ...) -> None: ...
