import pytest
from unittest.mock import AsyncMock, patch
from bindu.utils.agent_token_utils import (
    get_client_credentials_token,
    get_agent_token_from_credentials_file,
    introspect_token,
    revoke_token,
    create_bearer_header,
    validate_token_and_get_subject,
)
from bindu.auth.hydra.registration import AgentCredentials


@pytest.fixture
def mock_http_client():
    with patch("bindu.utils.agent_token_utils.http_client") as mock:
        yield mock


@pytest.mark.asyncio
async def test_get_client_credentials_token_success(mock_http_client):
    mock_post = AsyncMock()
    mock_post.status = 200
    mock_post.json.return_value = {
        "access_token": "token123",
        "token_type": "bearer",
        "expires_in": 3600,
    }

    # Mock the return value of the async context manager
    mock_client = AsyncMock()
    mock_client.post.return_value = mock_post
    mock_http_client.return_value.__aenter__.return_value = mock_client

    result = await get_client_credentials_token("client1", "secret1", "scope1")

    assert result == {
        "access_token": "token123",
        "token_type": "bearer",
        "expires_in": 3600,
    }
    mock_client.post.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_client_credentials_token_failure(mock_http_client):
    mock_post = AsyncMock()
    mock_post.status = 401
    mock_post.text.return_value = "Unauthorized"

    mock_client = AsyncMock()
    mock_client.post.return_value = mock_post
    mock_http_client.return_value.__aenter__.return_value = mock_client

    result = await get_client_credentials_token("client1", "secret1")
    assert result is None


@pytest.mark.asyncio
async def test_get_client_credentials_token_exception(mock_http_client):
    mock_http_client.side_effect = Exception("Test Error")
    result = await get_client_credentials_token("client1", "secret1")
    assert result is None


@pytest.mark.asyncio
@patch("bindu.utils.agent_token_utils.load_agent_credentials")
@patch("bindu.utils.agent_token_utils.get_client_credentials_token")
async def test_get_agent_token_from_credentials_file_success(mock_get_token, mock_load):
    credentials = AgentCredentials(
        agent_id="agent1",
        client_id="id1",
        client_secret="secret1",
        scopes=["s1"],
        created_at="2023-10-27T10:00:00Z",
    )
    mock_load.return_value = credentials
    mock_get_token.return_value = {"access_token": "token_from_cred"}

    result = await get_agent_token_from_credentials_file("agent1", "dir")
    assert result == "token_from_cred"


@pytest.mark.asyncio
@patch("bindu.utils.agent_token_utils.load_agent_credentials")
async def test_get_agent_token_from_credentials_file_not_found(mock_load):
    mock_load.return_value = None
    result = await get_agent_token_from_credentials_file("agent1", "dir")
    assert result is None


@pytest.mark.asyncio
@patch("bindu.utils.agent_token_utils.load_agent_credentials")
@patch("bindu.utils.agent_token_utils.get_client_credentials_token")
async def test_get_agent_token_from_credentials_file_no_token(
    mock_get_token, mock_load
):
    credentials = AgentCredentials(
        agent_id="agent1",
        client_id="id1",
        client_secret="secret1",
        scopes=["s1"],
        created_at="2023-10-27T10:00:00Z",
    )
    mock_load.return_value = credentials
    mock_get_token.return_value = None
    result = await get_agent_token_from_credentials_file("agent1", "dir")
    assert result is None


@pytest.mark.asyncio
@patch("bindu.auth.hydra.client.HydraClient")
async def test_introspect_token_success(mock_hydra_client):
    mock_client = AsyncMock()
    mock_client.introspect_token.return_value = {"active": True, "sub": "subj1"}
    mock_hydra_client.return_value.__aenter__.return_value = mock_client

    result = await introspect_token("test-token")
    assert result == {"active": True, "sub": "subj1"}


@pytest.mark.asyncio
@patch("bindu.auth.hydra.client.HydraClient")
async def test_introspect_token_exception(mock_hydra_client):
    mock_hydra_client.side_effect = Exception("error")
    result = await introspect_token("test")
    assert result is None


@pytest.mark.asyncio
@patch("bindu.auth.hydra.client.HydraClient")
async def test_revoke_token_success(mock_hydra_client):
    mock_client = AsyncMock()
    mock_client.revoke_token.return_value = True
    mock_hydra_client.return_value.__aenter__.return_value = mock_client

    result = await revoke_token("test-token")
    assert result is True


@pytest.mark.asyncio
@patch("bindu.auth.hydra.client.HydraClient")
async def test_revoke_token_exception(mock_hydra_client):
    mock_hydra_client.side_effect = Exception("error")
    result = await revoke_token("test")
    assert result is False


def test_create_bearer_header():
    assert create_bearer_header("my-token") == {"Authorization": "Bearer my-token"}


@pytest.mark.asyncio
@patch("bindu.utils.agent_token_utils.introspect_token")
async def test_validate_token_and_get_subject_valid(mock_introspect):
    mock_introspect.return_value = {"active": True, "sub": "subject1"}
    result = await validate_token_and_get_subject("token1")
    assert result == "subject1"


@pytest.mark.asyncio
@patch("bindu.utils.agent_token_utils.introspect_token")
async def test_validate_token_and_get_subject_invalid(mock_introspect):
    mock_introspect.return_value = {"active": False}
    result = await validate_token_and_get_subject("token1")
    assert result is None


@pytest.mark.asyncio
@patch("bindu.utils.agent_token_utils.introspect_token")
async def test_validate_token_and_get_subject_none(mock_introspect):
    mock_introspect.return_value = None
    result = await validate_token_and_get_subject("token1")
    assert result is None
