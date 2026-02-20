import json
from uuid import uuid4

from bindu.server.endpoints.a2a_protocol import validate_a2a_request_payload


def _parse_error_response(response) -> dict:
    return json.loads(response.body.decode("utf-8"))


def test_validate_a2a_request_rejects_invalid_json():
    _, error_response = validate_a2a_request_payload(b"{invalid")

    assert error_response is not None
    payload = _parse_error_response(error_response)
    assert payload["error"]["code"] == -32700


def test_validate_a2a_request_rejects_missing_method():
    data = json.dumps({"jsonrpc": "2.0", "id": "1", "params": {}}).encode()
    _, error_response = validate_a2a_request_payload(data)

    assert error_response is not None
    payload = _parse_error_response(error_response)
    assert payload["error"]["code"] == -32600


def test_validate_a2a_request_rejects_non_object_json():
    data = json.dumps(["not", "an", "object"]).encode()
    _, error_response = validate_a2a_request_payload(data)

    assert error_response is not None
    payload = _parse_error_response(error_response)
    assert payload["error"]["code"] == -32600


def test_validate_a2a_request_rejects_invalid_message_params():
    data = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "message/send",
            "params": {"configuration": {"acceptedOutputModes": ["text/plain"]}},
        }
    ).encode()

    _, error_response = validate_a2a_request_payload(data)

    assert error_response is not None
    payload = _parse_error_response(error_response)
    assert payload["error"]["code"] == -32600


def test_validate_a2a_request_accepts_valid_message_send():
    message_id = str(uuid4())
    context_id = str(uuid4())
    task_id = str(uuid4())

    data = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "message/send",
            "params": {
                "configuration": {"acceptedOutputModes": ["text/plain"]},
                "message": {
                    "messageId": message_id,
                    "contextId": context_id,
                    "taskId": task_id,
                    "kind": "message",
                    "role": "user",
                    "parts": [{"kind": "text", "text": "hello"}],
                },
            },
        }
    ).encode()

    a2a_request, error_response = validate_a2a_request_payload(data)

    assert error_response is None
    assert a2a_request is not None
