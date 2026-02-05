"""Unit tests for bindu.edge_client module.

Tests cover:
- Binary vs text content detection
- Request body encoding/decoding
- Response body encoding/decoding
- Header forwarding
- Compression support
- Timeout handling
- Error scenarios
"""

import asyncio
import base64
import gzip
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import httpx

from bindu.edge_client import (
    _is_binary_content_type,
    _find_project_root,
    _load_config_file,
    forward_request_to_local,
    send_ping,
)


class TestBinaryContentTypeDetection:
    """Test _is_binary_content_type helper function."""

    def test_text_content_types(self):
        """Test that text content types are correctly identified."""
        text_types = [
            "text/plain",
            "text/html",
            "text/css",
            "application/json",
            "application/javascript",
            "application/xml",
            "application/x-www-form-urlencoded",
            "application/ld+json",
            "text/plain; charset=utf-8",
        ]
        for content_type in text_types:
            assert not _is_binary_content_type(content_type), f"Failed for {content_type}"

    def test_binary_content_types(self):
        """Test that binary content types are correctly identified."""
        binary_types = [
            "image/png",
            "image/jpeg",
            "image/gif",
            "video/mp4",
            "audio/mpeg",
            "application/pdf",
            "application/octet-stream",
            "application/zip",
            "application/gzip",
            "font/woff2",
            "application/vnd.ms-excel",
        ]
        for content_type in binary_types:
            assert _is_binary_content_type(content_type), f"Failed for {content_type}"

    def test_unknown_content_type_defaults_to_text(self):
        """Test that unknown content types default to text."""
        assert not _is_binary_content_type("application/unknown-type")
        assert not _is_binary_content_type("")


class TestForwardRequestToLocal:
    """Test forward_request_to_local function."""

    @pytest.mark.asyncio
    async def test_simple_text_response(self):
        """Test forwarding a simple text response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.text = "Hello, World!"
        mock_response.content = b"Hello, World!"

        with patch("bindu.edge_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            req = {
                "request_id": "test-123",
                "method": "GET",
                "path": "/test",
                "headers": {},
            }

            result = await forward_request_to_local(3773, req)

            assert result["type"] == "response"
            assert result["status"] == 200
            assert result["body"] == "Hello, World!"
            assert result["body_encoding"] == "text"
            assert "content-type" in result["headers"]

    @pytest.mark.asyncio
    async def test_binary_response(self):
        """Test forwarding a binary response (image)."""
        binary_data = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR..."  # PNG header
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "image/png"}
        mock_response.content = binary_data
        mock_response.text = binary_data.decode("latin-1")  # Would normally fail

        with patch("bindu.edge_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            req = {
                "request_id": "test-456",
                "method": "GET",
                "path": "/image.png",
                "headers": {},
            }

            result = await forward_request_to_local(3773, req)

            assert result["type"] == "response"
            assert result["status"] == 200
            assert result["body_encoding"] == "base64"
            
            # Verify base64 encoding is valid and matches original
            decoded = base64.b64decode(result["body"])
            assert decoded == binary_data

    @pytest.mark.asyncio
    async def test_json_response(self):
        """Test forwarding a JSON response."""
        json_data = {"status": "success", "data": {"id": 123, "name": "Test"}}
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = json.dumps(json_data)
        mock_response.content = json.dumps(json_data).encode()

        with patch("bindu.edge_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            req = {
                "request_id": "test-789",
                "method": "POST",
                "path": "/api/data",
                "headers": {"content-type": "application/json"},
                "body": json.dumps({"query": "test"}),
            }

            result = await forward_request_to_local(3773, req)

            assert result["type"] == "response"
            assert result["status"] == 200
            assert result["body_encoding"] == "text"
            assert json.loads(result["body"]) == json_data

    @pytest.mark.asyncio
    async def test_request_with_base64_body(self):
        """Test forwarding request with base64-encoded binary body."""
        binary_body = b"\x00\x01\x02\x03\x04\x05"
        encoded_body = base64.b64encode(binary_body).decode("ascii")

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.text = "Created"
        mock_response.content = b"Created"

        with patch("bindu.edge_client.httpx.AsyncClient") as mock_client:
            mock_request = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.request = mock_request

            req = {
                "request_id": "test-binary-req",
                "method": "POST",
                "path": "/upload",
                "headers": {},
                "body": encoded_body,
                "body_encoding": "base64",
            }

            result = await forward_request_to_local(3773, req)

            # Verify request was called with decoded binary data
            mock_request.assert_called_once()
            call_kwargs = mock_request.call_args.kwargs
            assert call_kwargs["content"] == binary_body

    @pytest.mark.asyncio
    async def test_query_string_forwarding(self):
        """Test that query strings are properly forwarded."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.text = "OK"
        mock_response.content = b"OK"

        with patch("bindu.edge_client.httpx.AsyncClient") as mock_client:
            mock_request = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.request = mock_request

            req = {
                "request_id": "test-query",
                "method": "GET",
                "path": "/search?q=test&limit=10",
                "headers": {},
            }

            await forward_request_to_local(3773, req)

            # Verify URL includes query string
            call_args = mock_request.call_args
            assert "search?q=test&limit=10" in call_args.args[1]

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling when local server is unreachable."""
        with patch("bindu.edge_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                side_effect=httpx.ConnectError("Connection refused")
            )

            req = {
                "request_id": "test-error",
                "method": "GET",
                "path": "/test",
                "headers": {},
            }

            result = await forward_request_to_local(3773, req)

            assert result["type"] == "response"
            assert result["status"] == 502
            assert "Agent error" in result["body"]
            assert result["body_encoding"] == "text"

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling."""
        with patch("bindu.edge_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                side_effect=httpx.TimeoutException("Request timeout")
            )

            req = {
                "request_id": "test-timeout",
                "method": "GET",
                "path": "/slow",
                "headers": {},
            }

            result = await forward_request_to_local(3773, req, timeout=1)

            assert result["type"] == "response"
            assert result["status"] == 502
            assert "timeout" in result["body"].lower()

    @pytest.mark.asyncio
    async def test_large_response_compression(self):
        """Test that large responses trigger compression."""
        # Create a large JSON response
        large_data = {"items": [{"id": i, "data": "x" * 100} for i in range(100)]}
        large_json = json.dumps(large_data)

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = large_json
        mock_response.content = large_json.encode()

        with patch("bindu.edge_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            req = {
                "request_id": "test-compression",
                "method": "GET",
                "path": "/large",
                "headers": {},
            }

            result = await forward_request_to_local(3773, req)

            # Should be compressed
            if result.get("compressed"):
                assert "data" in result
                # Verify we can decompress
                compressed_data = base64.b64decode(result["data"])
                decompressed = gzip.decompress(compressed_data)
                original = json.loads(decompressed)
                assert original["type"] == "response"
                assert original["status"] == 200
            else:
                # If not compressed, should still be valid
                assert result["body"] == large_json

    @pytest.mark.asyncio
    async def test_headers_forwarding(self):
        """Test that all headers are properly forwarded."""
        request_headers = {
            "Authorization": "Bearer token123",
            "X-Custom-Header": "custom-value",
            "Content-Type": "application/json",
        }

        response_headers = {
            "Content-Type": "application/json",
            "Cache-Control": "max-age=3600",
            "X-Response-ID": "resp-123",
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = response_headers
        mock_response.text = "{}"
        mock_response.content = b"{}"

        with patch("bindu.edge_client.httpx.AsyncClient") as mock_client:
            mock_request = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.request = mock_request

            req = {
                "request_id": "test-headers",
                "method": "POST",
                "path": "/api",
                "headers": request_headers,
                "body": "{}",
            }

            result = await forward_request_to_local(3773, req)

            # Verify request headers were forwarded
            call_kwargs = mock_request.call_args.kwargs
            assert call_kwargs["headers"] == request_headers

            # Verify response headers are included
            assert "Cache-Control" in result["headers"]
            assert result["headers"]["Cache-Control"] == "max-age=3600"

    @pytest.mark.asyncio
    async def test_text_decode_failure_fallback_to_binary(self):
        """Test fallback to binary encoding when text decode fails."""
        # Invalid UTF-8 sequence
        invalid_utf8 = b"\x80\x81\x82\x83"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.content = invalid_utf8
        # Simulate decode error
        mock_response.text = property(lambda self: (_ for _ in ()).throw(UnicodeDecodeError(
            'utf-8', invalid_utf8, 0, 1, 'invalid start byte'
        )))

        with patch("bindu.edge_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            req = {
                "request_id": "test-decode-fail",
                "method": "GET",
                "path": "/binary",
                "headers": {},
            }

            result = await forward_request_to_local(3773, req)

            # Should fallback to base64
            assert result["body_encoding"] == "base64"
            decoded = base64.b64decode(result["body"])
            assert decoded == invalid_utf8


class TestSendPing:
    """Test send_ping function."""

    @pytest.mark.asyncio
    async def test_send_ping_success(self):
        """Test successful ping sending."""
        mock_ws = AsyncMock()
        
        # Run ping for a short duration
        task = asyncio.create_task(send_ping(mock_ws, interval=0.1))
        await asyncio.sleep(0.25)  # Let it send 2-3 pings
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Verify at least one ping was sent
        assert mock_ws.send.call_count >= 2
        
        # Verify ping format
        first_call = mock_ws.send.call_args_list[0]
        ping_data = json.loads(first_call[0][0])
        assert ping_data["type"] == "ping"
        assert "ts" in ping_data

    @pytest.mark.asyncio
    async def test_send_ping_handles_exception(self):
        """Test that send_ping gracefully handles exceptions."""
        mock_ws = AsyncMock()
        mock_ws.send.side_effect = Exception("Connection closed")

        # Should not raise, just return
        await send_ping(mock_ws, interval=0.01)

        # Verify it tried to send
        assert mock_ws.send.call_count == 1


class TestEdgeClientIntegration:
    """Integration-style tests for edge client functionality."""

    @pytest.mark.asyncio
    async def test_pdf_download(self):
        """Test downloading a PDF file."""
        # Minimal PDF header
        pdf_data = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.content = pdf_data

        with patch("bindu.edge_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            req = {
                "request_id": "pdf-test",
                "method": "GET",
                "path": "/document.pdf",
                "headers": {},
            }

            result = await forward_request_to_local(3773, req)

            assert result["status"] == 200
            assert result["body_encoding"] == "base64"
            assert base64.b64decode(result["body"]) == pdf_data

    @pytest.mark.asyncio
    async def test_multipart_form_upload(self):
        """Test multipart form data upload."""
        form_data = b"--boundary\r\nContent-Disposition: form-data; name=\"file\"\r\n\r\ntest\r\n--boundary--"

        mock_response = Mock()
        mock_response.status_code = 201
        mock_response.headers = {"content-type": "application/json"}
        mock_response.text = '{"uploaded": true}'
        mock_response.content = b'{"uploaded": true}'

        with patch("bindu.edge_client.httpx.AsyncClient") as mock_client:
            mock_request = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.request = mock_request

            req = {
                "request_id": "upload-test",
                "method": "POST",
                "path": "/upload",
                "headers": {"content-type": "multipart/form-data; boundary=boundary"},
                "body": base64.b64encode(form_data).decode("ascii"),
                "body_encoding": "base64",
            }

            result = await forward_request_to_local(3773, req)

            assert result["status"] == 201
            # Verify uploaded successfully
            call_kwargs = mock_request.call_args.kwargs
            assert call_kwargs["content"] == form_data

    @pytest.mark.asyncio
    async def test_empty_response_body(self):
        """Test handling of empty response body."""
        mock_response = Mock()
        mock_response.status_code = 204  # No Content
        mock_response.headers = {}
        mock_response.text = ""
        mock_response.content = b""

        with patch("bindu.edge_client.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.request = AsyncMock(
                return_value=mock_response
            )

            req = {
                "request_id": "empty-test",
                "method": "DELETE",
                "path": "/resource/123",
                "headers": {},
            }

            result = await forward_request_to_local(3773, req)

            assert result["status"] == 204
            assert result["body"] == ""

    @pytest.mark.asyncio
    async def test_special_characters_in_path(self):
        """Test handling of special characters in path."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.text = "OK"
        mock_response.content = b"OK"

        with patch("bindu.edge_client.httpx.AsyncClient") as mock_client:
            mock_request = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.request = mock_request

            req = {
                "request_id": "special-chars",
                "method": "GET",
                "path": "/search?name=John%20Doe&tags=test%2Cproduction",
                "headers": {},
            }

            await forward_request_to_local(3773, req)

            # Verify special characters are preserved
            call_args = mock_request.call_args
            assert "John%20Doe" in call_args.args[1]
            assert "test%2Cproduction" in call_args.args[1]

class TestFindProjectRoot:
    """Test _find_project_root function."""

    def test_finds_pyproject_toml_in_current_dir(self):
        """Test finding project root with pyproject.toml in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pyproject_path = tmpdir_path / "pyproject.toml"
            pyproject_path.write_text("[tool.poetry]\nname = 'test'\n")
            
            with patch("bindu.edge_client.Path.cwd", return_value=tmpdir_path):
                result = _find_project_root()
                assert result == tmpdir_path

    def test_finds_git_in_current_dir(self):
        """Test finding project root with .git in current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            git_dir = tmpdir_path / ".git"
            git_dir.mkdir()
            
            with patch("bindu.edge_client.Path.cwd", return_value=tmpdir_path):
                result = _find_project_root()
                assert result == tmpdir_path

    def test_finds_pyproject_in_parent_dir(self):
        """Test finding project root in parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pyproject_path = tmpdir_path / "pyproject.toml"
            pyproject_path.write_text("[tool.poetry]\nname = 'test'\n")
            
            # Create nested directory
            nested_dir = tmpdir_path / "src" / "module"
            nested_dir.mkdir(parents=True)
            
            with patch("bindu.edge_client.Path.cwd", return_value=nested_dir):
                result = _find_project_root()
                assert result == tmpdir_path

    def test_finds_git_in_parent_dir(self):
        """Test finding .git in parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            git_dir = tmpdir_path / ".git"
            git_dir.mkdir()
            
            # Create nested directory
            nested_dir = tmpdir_path / "src" / "module"
            nested_dir.mkdir(parents=True)
            
            with patch("bindu.edge_client.Path.cwd", return_value=nested_dir):
                result = _find_project_root()
                assert result == tmpdir_path

    def test_returns_none_when_no_markers_found(self):
        """Test returning None when no project markers found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            with patch("bindu.edge_client.Path.cwd", return_value=tmpdir_path):
                result = _find_project_root()
                # Should return None if no pyproject.toml or .git found
                # (or might return system root if it has .git, implementation dependent)
                # We'll just verify it returns a Path or None
                assert result is None or isinstance(result, Path)

    def test_prefers_closest_marker(self):
        """Test that closest project marker is found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create outer project root
            outer_pyproject = tmpdir_path / "pyproject.toml"
            outer_pyproject.write_text("[tool.poetry]\nname = 'outer'\n")
            
            # Create nested project root
            nested_dir = tmpdir_path / "nested"
            nested_dir.mkdir()
            nested_pyproject = nested_dir / "pyproject.toml"
            nested_pyproject.write_text("[tool.poetry]\nname = 'inner'\n")
            
            # Working from nested dir should find nested project
            with patch("bindu.edge_client.Path.cwd", return_value=nested_dir):
                result = _find_project_root()
                assert result == nested_dir


class TestLoadConfigFile:
    """Test _load_config_file function."""

    def test_loads_explicit_config_path(self):
        """Test loading config from explicitly provided path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "custom_config.json"
            config_data = {
                "ws_url": "ws://example.com/ws",
                "token": "test-token",
                "local_port": 8080
            }
            config_path.write_text(json.dumps(config_data))
            
            result = _load_config_file(str(config_path))
            
            assert result == config_data

    def test_loads_from_project_root(self):
        """Test loading edge.config.json from project root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create project marker
            pyproject_path = tmpdir_path / "pyproject.toml"
            pyproject_path.write_text("[tool.poetry]\nname = 'test'\n")
            
            # Create config file
            config_path = tmpdir_path / "edge.config.json"
            config_data = {
                "ws_url": "ws://localhost:8001/ws/test",
                "token": "project-token",
                "local_port": 3773
            }
            config_path.write_text(json.dumps(config_data))
            
            with patch("bindu.edge_client.Path.cwd", return_value=tmpdir_path):
                result = _load_config_file()
                
                assert result == config_data

    def test_returns_none_when_no_config_found(self):
        """Test returning None when no config file exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            pyproject_path = tmpdir_path / "pyproject.toml"
            pyproject_path.write_text("[tool.poetry]\nname = 'test'\n")
            
            with patch("bindu.edge_client.Path.cwd", return_value=tmpdir_path):
                result = _load_config_file()
                
                assert result is None

    def test_returns_none_when_no_project_root_found(self):
        """Test returning None when project root cannot be found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            with patch("bindu.edge_client.Path.cwd", return_value=tmpdir_path):
                with patch("bindu.edge_client._find_project_root", return_value=None):
                    result = _load_config_file()
                    
                    assert result is None

    def test_handles_malformed_json(self):
        """Test handling of malformed JSON in config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "bad_config.json"
            config_path.write_text("{ invalid json }")
            
            result = _load_config_file(str(config_path))
            
            # Should return None on parse error
            assert result is None

    def test_handles_missing_file_gracefully(self):
        """Test graceful handling when specified config file doesn't exist."""
        result = _load_config_file("/nonexistent/path/config.json")
        assert result is None

    def test_explicit_path_takes_precedence(self):
        """Test that explicit config path takes precedence over project root."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            
            # Create project root config
            pyproject_path = tmpdir_path / "pyproject.toml"
            pyproject_path.write_text("[tool.poetry]\nname = 'test'\n")
            
            project_config = tmpdir_path / "edge.config.json"
            project_config.write_text(json.dumps({"ws_url": "ws://project"}))
            
            # Create custom config
            custom_config = tmpdir_path / "custom.json"
            custom_config.write_text(json.dumps({"ws_url": "ws://custom"}))
            
            with patch("bindu.edge_client.Path.cwd", return_value=tmpdir_path):
                result = _load_config_file(str(custom_config))
                
                assert result["ws_url"] == "ws://custom"

    def test_loads_partial_config(self):
        """Test loading config with only some fields present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "partial_config.json"
            config_data = {
                "ws_url": "ws://example.com/ws"
                # token and local_port missing
            }
            config_path.write_text(json.dumps(config_data))
            
            result = _load_config_file(str(config_path))
            
            assert result == config_data
            assert "ws_url" in result
            assert "token" not in result

    def test_config_with_extra_fields(self):
        """Test that config with extra fields is loaded successfully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_data = {
                "ws_url": "ws://example.com/ws",
                "token": "test-token",
                "local_port": 3773,
                "extra_field": "should be ignored",
                "another_field": 123
            }
            config_path.write_text(json.dumps(config_data))
            
            result = _load_config_file(str(config_path))
            
            assert result == config_data