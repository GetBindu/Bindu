from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import (
    Any as _Any,
    ClassVar as _ClassVar,
    Optional as _Optional,
    Union as _Union,
)

DESCRIPTOR: _descriptor.FileDescriptor

class Message(_message.Message):
    __slots__ = (
        "message_id",
        "context_id",
        "task_id",
        "reference_task_ids",
        "kind",
        "metadata",
        "parts",
        "role",
        "extensions",
    )
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[str] = ...
        ) -> None: ...

    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    REFERENCE_TASK_IDS_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    PARTS_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    EXTENSIONS_FIELD_NUMBER: _ClassVar[int]
    message_id: str
    context_id: str
    task_id: str
    reference_task_ids: _containers.RepeatedScalarFieldContainer[str]
    kind: str
    metadata: _containers.ScalarMap[str, str]
    parts: _containers.RepeatedCompositeFieldContainer[Part]
    role: str
    extensions: _containers.RepeatedScalarFieldContainer[str]
    def __init__(
        self,
        message_id: _Optional[str] = ...,
        context_id: _Optional[str] = ...,
        task_id: _Optional[str] = ...,
        reference_task_ids: _Optional[_Iterable[str]] = ...,
        kind: _Optional[str] = ...,
        metadata: _Optional[_Mapping[str, str]] = ...,
        parts: _Optional[_Iterable[_Union[Part, _Mapping]]] = ...,
        role: _Optional[str] = ...,
        extensions: _Optional[_Iterable[str]] = ...,
    ) -> None: ...

class Part(_message.Message):
    __slots__ = ("text", "file", "data")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    FILE_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    text: TextPart
    file: FilePart
    data: DataPart
    def __init__(
        self,
        text: _Optional[_Union[TextPart, _Mapping]] = ...,
        file: _Optional[_Union[FilePart, _Mapping]] = ...,
        data: _Optional[_Union[DataPart, _Mapping]] = ...,
    ) -> None: ...

class TextPart(_message.Message):
    __slots__ = ("text", "metadata", "embeddings")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[str] = ...
        ) -> None: ...

    TEXT_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    EMBEDDINGS_FIELD_NUMBER: _ClassVar[int]
    text: str
    metadata: _containers.ScalarMap[str, str]
    embeddings: _containers.RepeatedScalarFieldContainer[float]
    def __init__(
        self,
        text: _Optional[str] = ...,
        metadata: _Optional[_Mapping[str, str]] = ...,
        embeddings: _Optional[_Iterable[float]] = ...,
    ) -> None: ...

class FilePart(_message.Message):
    __slots__ = ("file_id", "mime_type", "filename", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[str] = ...
        ) -> None: ...

    FILE_ID_FIELD_NUMBER: _ClassVar[int]
    MIME_TYPE_FIELD_NUMBER: _ClassVar[int]
    FILENAME_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    file_id: str
    mime_type: str
    filename: str
    metadata: _containers.ScalarMap[str, str]
    def __init__(
        self,
        file_id: _Optional[str] = ...,
        mime_type: _Optional[str] = ...,
        filename: _Optional[str] = ...,
        metadata: _Optional[_Mapping[str, str]] = ...,
    ) -> None: ...

class DataPart(_message.Message):
    __slots__ = ("mime_type", "data", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[str] = ...
        ) -> None: ...

    MIME_TYPE_FIELD_NUMBER: _ClassVar[int]
    DATA_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    mime_type: str
    data: bytes
    metadata: _containers.ScalarMap[str, str]
    def __init__(
        self,
        mime_type: _Optional[str] = ...,
        data: _Optional[bytes] = ...,
        metadata: _Optional[_Mapping[str, str]] = ...,
    ) -> None: ...

class Task(_message.Message):
    __slots__ = (
        "id",
        "context_id",
        "kind",
        "status",
        "artifacts",
        "history",
        "metadata",
    )
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[str] = ...
        ) -> None: ...

    ID_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    ARTIFACTS_FIELD_NUMBER: _ClassVar[int]
    HISTORY_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    id: str
    context_id: str
    kind: str
    status: TaskStatus
    artifacts: _containers.RepeatedCompositeFieldContainer[Artifact]
    history: _containers.RepeatedCompositeFieldContainer[Message]
    metadata: _containers.ScalarMap[str, str]
    def __init__(
        self,
        id: _Optional[str] = ...,
        context_id: _Optional[str] = ...,
        kind: _Optional[str] = ...,
        status: _Optional[_Union[TaskStatus, _Mapping]] = ...,
        artifacts: _Optional[_Iterable[_Union[Artifact, _Mapping]]] = ...,
        history: _Optional[_Iterable[_Union[Message, _Mapping]]] = ...,
        metadata: _Optional[_Mapping[str, str]] = ...,
    ) -> None: ...

class TaskStatus(_message.Message):
    __slots__ = ("state", "timestamp", "message")
    STATE_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    state: str
    timestamp: str
    message: Message
    def __init__(
        self,
        state: _Optional[str] = ...,
        timestamp: _Optional[str] = ...,
        message: _Optional[_Union[Message, _Mapping]] = ...,
    ) -> None: ...

class Artifact(_message.Message):
    __slots__ = ("artifact_id", "name", "parts", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[str] = ...
        ) -> None: ...

    ARTIFACT_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    PARTS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    artifact_id: str
    name: str
    parts: _containers.RepeatedCompositeFieldContainer[Part]
    metadata: _containers.ScalarMap[str, str]
    def __init__(
        self,
        artifact_id: _Optional[str] = ...,
        name: _Optional[str] = ...,
        parts: _Optional[_Iterable[_Union[Part, _Mapping]]] = ...,
        metadata: _Optional[_Mapping[str, str]] = ...,
    ) -> None: ...

class MessageSendRequest(_message.Message):
    __slots__ = ("message", "configuration")
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    CONFIGURATION_FIELD_NUMBER: _ClassVar[int]
    message: Message
    configuration: TaskConfiguration
    def __init__(
        self,
        message: _Optional[_Union[Message, _Mapping]] = ...,
        configuration: _Optional[_Union[TaskConfiguration, _Mapping]] = ...,
    ) -> None: ...

class MessageSendResponse(_message.Message):
    __slots__ = ("task",)
    TASK_FIELD_NUMBER: _ClassVar[int]
    task: Task
    def __init__(self, task: _Optional[_Union[Task, _Mapping]] = ...) -> None: ...

class TaskQueryRequest(_message.Message):
    __slots__ = ("task_id",)
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    def __init__(self, task_id: _Optional[str] = ...) -> None: ...

class ListTasksRequest(_message.Message):
    __slots__ = ("context_id", "limit", "cursor")
    CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    context_id: str
    limit: int
    cursor: str
    def __init__(
        self,
        context_id: _Optional[str] = ...,
        limit: _Optional[int] = ...,
        cursor: _Optional[str] = ...,
    ) -> None: ...

class TaskListResponse(_message.Message):
    __slots__ = ("tasks", "next_cursor")
    TASKS_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    tasks: _containers.RepeatedCompositeFieldContainer[Task]
    next_cursor: str
    def __init__(
        self,
        tasks: _Optional[_Iterable[_Union[Task, _Mapping]]] = ...,
        next_cursor: _Optional[str] = ...,
    ) -> None: ...

class TaskIdRequest(_message.Message):
    __slots__ = ("task_id",)
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    def __init__(self, task_id: _Optional[str] = ...) -> None: ...

class TaskFeedbackRequest(_message.Message):
    __slots__ = ("task_id", "feedback", "rating", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[str] = ...
        ) -> None: ...

    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    FEEDBACK_FIELD_NUMBER: _ClassVar[int]
    RATING_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    feedback: str
    rating: int
    metadata: _containers.ScalarMap[str, str]
    def __init__(
        self,
        task_id: _Optional[str] = ...,
        feedback: _Optional[str] = ...,
        rating: _Optional[int] = ...,
        metadata: _Optional[_Mapping[str, str]] = ...,
    ) -> None: ...

class TaskFeedbackResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ...) -> None: ...

class ListContextsRequest(_message.Message):
    __slots__ = ("limit", "cursor")
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    CURSOR_FIELD_NUMBER: _ClassVar[int]
    limit: int
    cursor: str
    def __init__(
        self, limit: _Optional[int] = ..., cursor: _Optional[str] = ...
    ) -> None: ...

class ContextListResponse(_message.Message):
    __slots__ = ("contexts", "next_cursor")
    CONTEXTS_FIELD_NUMBER: _ClassVar[int]
    NEXT_CURSOR_FIELD_NUMBER: _ClassVar[int]
    contexts: _containers.RepeatedCompositeFieldContainer[Context]
    next_cursor: str
    def __init__(
        self,
        contexts: _Optional[_Iterable[_Union[Context, _Mapping]]] = ...,
        next_cursor: _Optional[str] = ...,
    ) -> None: ...

class Context(_message.Message):
    __slots__ = ("context_id", "messages", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[str] = ...
        ) -> None: ...

    CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    MESSAGES_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    context_id: str
    messages: _containers.RepeatedCompositeFieldContainer[Message]
    metadata: _containers.ScalarMap[str, str]
    def __init__(
        self,
        context_id: _Optional[str] = ...,
        messages: _Optional[_Iterable[_Union[Message, _Mapping]]] = ...,
        metadata: _Optional[_Mapping[str, str]] = ...,
    ) -> None: ...

class ContextIdRequest(_message.Message):
    __slots__ = ("context_id",)
    CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    context_id: str
    def __init__(self, context_id: _Optional[str] = ...) -> None: ...

class ContextClearResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ...) -> None: ...

class TaskConfiguration(_message.Message):
    __slots__ = ("accepted_output_modes", "long_running", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[str] = ...
        ) -> None: ...

    ACCEPTED_OUTPUT_MODES_FIELD_NUMBER: _ClassVar[int]
    LONG_RUNNING_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    accepted_output_modes: _containers.RepeatedScalarFieldContainer[str]
    long_running: bool
    metadata: _containers.ScalarMap[str, str]
    def __init__(
        self,
        accepted_output_modes: _Optional[_Iterable[str]] = ...,
        long_running: bool = ...,
        metadata: _Optional[_Mapping[str, str]] = ...,
    ) -> None: ...

class PushNotificationConfig(_message.Message):
    __slots__ = ("id", "url", "token", "authentication")
    ID_FIELD_NUMBER: _ClassVar[int]
    URL_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    AUTHENTICATION_FIELD_NUMBER: _ClassVar[int]
    id: str
    url: str
    token: str
    authentication: _Any
    def __init__(
        self,
        id: _Optional[str] = ...,
        url: _Optional[str] = ...,
        token: _Optional[str] = ...,
        authentication: _Optional[_Union[_Any, _Mapping]] = ...,
    ) -> None: ...

class TaskPushNotificationConfig(_message.Message):
    __slots__ = ("id", "push_notification_config", "long_running")
    ID_FIELD_NUMBER: _ClassVar[int]
    PUSH_NOTIFICATION_CONFIG_FIELD_NUMBER: _ClassVar[int]
    LONG_RUNNING_FIELD_NUMBER: _ClassVar[int]
    id: str
    push_notification_config: PushNotificationConfig
    long_running: bool
    def __init__(
        self,
        id: _Optional[str] = ...,
        push_notification_config: _Optional[
            _Union[PushNotificationConfig, _Mapping]
        ] = ...,
        long_running: bool = ...,
    ) -> None: ...

class SetTaskPushNotificationRequest(_message.Message):
    __slots__ = ("config",)
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    config: TaskPushNotificationConfig
    def __init__(
        self, config: _Optional[_Union[TaskPushNotificationConfig, _Mapping]] = ...
    ) -> None: ...

class GetTaskPushNotificationRequest(_message.Message):
    __slots__ = ("task_id",)
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    def __init__(self, task_id: _Optional[str] = ...) -> None: ...

class ListTaskPushNotificationsRequest(_message.Message):
    __slots__ = ("id",)
    ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    def __init__(self, id: _Optional[str] = ...) -> None: ...

class DeleteTaskPushNotificationRequest(_message.Message):
    __slots__ = ("id", "push_notification_config_id")
    ID_FIELD_NUMBER: _ClassVar[int]
    PUSH_NOTIFICATION_CONFIG_ID_FIELD_NUMBER: _ClassVar[int]
    id: str
    push_notification_config_id: str
    def __init__(
        self,
        id: _Optional[str] = ...,
        push_notification_config_id: _Optional[str] = ...,
    ) -> None: ...

class TaskPushNotificationListResponse(_message.Message):
    __slots__ = ("configs",)
    CONFIGS_FIELD_NUMBER: _ClassVar[int]
    configs: _containers.RepeatedCompositeFieldContainer[TaskPushNotificationConfig]
    def __init__(
        self,
        configs: _Optional[
            _Iterable[_Union[TaskPushNotificationConfig, _Mapping]]
        ] = ...,
    ) -> None: ...

class DeleteTaskPushNotificationResponse(_message.Message):
    __slots__ = ("config",)
    CONFIG_FIELD_NUMBER: _ClassVar[int]
    config: TaskPushNotificationConfig
    def __init__(
        self, config: _Optional[_Union[TaskPushNotificationConfig, _Mapping]] = ...
    ) -> None: ...

class TaskEvent(_message.Message):
    __slots__ = ("status_update", "artifact_update")
    STATUS_UPDATE_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_UPDATE_FIELD_NUMBER: _ClassVar[int]
    status_update: TaskStatusUpdateEvent
    artifact_update: TaskArtifactUpdateEvent
    def __init__(
        self,
        status_update: _Optional[_Union[TaskStatusUpdateEvent, _Mapping]] = ...,
        artifact_update: _Optional[_Union[TaskArtifactUpdateEvent, _Mapping]] = ...,
    ) -> None: ...

class TaskStatusUpdateEvent(_message.Message):
    __slots__ = ("task_id", "context_id", "final", "status", "metadata")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[str] = ...
        ) -> None: ...

    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    FINAL_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    context_id: str
    final: bool
    status: TaskStatus
    metadata: _containers.ScalarMap[str, str]
    def __init__(
        self,
        task_id: _Optional[str] = ...,
        context_id: _Optional[str] = ...,
        final: bool = ...,
        status: _Optional[_Union[TaskStatus, _Mapping]] = ...,
        metadata: _Optional[_Mapping[str, str]] = ...,
    ) -> None: ...

class TaskArtifactUpdateEvent(_message.Message):
    __slots__ = (
        "task_id",
        "context_id",
        "artifact",
        "append",
        "last_chunk",
        "metadata",
    )
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(
            self, key: _Optional[str] = ..., value: _Optional[str] = ...
        ) -> None: ...

    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_ID_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_FIELD_NUMBER: _ClassVar[int]
    APPEND_FIELD_NUMBER: _ClassVar[int]
    LAST_CHUNK_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    context_id: str
    artifact: Artifact
    append: bool
    last_chunk: bool
    metadata: _containers.ScalarMap[str, str]
    def __init__(
        self,
        task_id: _Optional[str] = ...,
        context_id: _Optional[str] = ...,
        artifact: _Optional[_Union[Artifact, _Mapping]] = ...,
        append: bool = ...,
        last_chunk: bool = ...,
        metadata: _Optional[_Mapping[str, str]] = ...,
    ) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ("service",)
    SERVICE_FIELD_NUMBER: _ClassVar[int]
    service: str
    def __init__(self, service: _Optional[str] = ...) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("status",)
    class ServingStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):  # type: ignore[conflicting-metaclass]
        __slots__ = ()
        UNKNOWN: _ClassVar[HealthCheckResponse.ServingStatus]
        SERVING: _ClassVar[HealthCheckResponse.ServingStatus]
        NOT_SERVING: _ClassVar[HealthCheckResponse.ServingStatus]

    UNKNOWN: HealthCheckResponse.ServingStatus
    SERVING: HealthCheckResponse.ServingStatus
    NOT_SERVING: HealthCheckResponse.ServingStatus
    STATUS_FIELD_NUMBER: _ClassVar[int]
    status: HealthCheckResponse.ServingStatus
    def __init__(
        self, status: _Optional[_Union[HealthCheckResponse.ServingStatus, str]] = ...
    ) -> None: ...
