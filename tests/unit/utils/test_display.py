"""Comprehensive tests for display utilities."""

from unittest.mock import MagicMock, patch

from bindu.utils.display import prepare_server_display


class TestPrepareServerDisplay:
    """Test server display preparation."""

    @patch("bindu.utils.display.Console")
    def test_basic_display(self, mock_console_class):
        """Test basic display without any parameters."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        prepare_server_display()

        # Should create console and print panels
        mock_console_class.assert_called_once()
        assert mock_console.print.call_count > 0

    @patch("bindu.utils.display.Console")
    def test_display_with_server_info(self, mock_console_class):
        """Test display with server host and port."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        prepare_server_display(host="localhost", port=3773)

        # Verify server info is displayed
        assert mock_console.print.call_count > 0
        # Check that server URL was printed
        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("localhost" in str(call) and "3773" in str(call) for call in calls)

    @patch("bindu.utils.display.Console")
    def test_display_with_agent_info(self, mock_console_class):
        """Test display with agent ID and DID."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        prepare_server_display(agent_id="test-agent", agent_did="did:bindu:test")

        # Verify agent info is displayed
        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("test-agent" in str(call) for call in calls)
        assert any("did:bindu:test" in str(call) for call in calls)

    @patch("bindu.utils.display.Console")
    def test_display_with_tunnel_url(self, mock_console_class):
        """Test display with tunnel URL."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        prepare_server_display(
            host="localhost", port=3773, tunnel_url="https://test.tunnel.getbindu.com"
        )

        # Verify tunnel URL is displayed
        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("test.tunnel.getbindu.com" in str(call) for call in calls)

    @patch("bindu.utils.display.Console")
    def test_display_with_oauth_credentials(self, mock_console_class):
        """Test display with OAuth credentials."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        prepare_server_display(client_id="test-client-id", client_secret="test-secret")

        # Verify OAuth info is displayed
        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("test-client-id" in str(call) for call in calls)
        assert any("curl" in str(call) for call in calls)

    @patch("bindu.utils.display.Console")
    def test_display_with_all_parameters(self, mock_console_class):
        """Test display with all parameters."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        prepare_server_display(
            host="0.0.0.0",
            port=8080,
            agent_id="full-agent",
            agent_did="did:bindu:full",
            client_id="client-123",
            client_secret="secret-456",
            tunnel_url="https://full.tunnel.com",
        )

        # Should print all information
        assert mock_console.print.call_count > 10

    @patch("bindu.utils.display.Console")
    @patch("sys.stdout")
    def test_utf8_reconfigure(self, mock_stdout, mock_console_class):
        """Test UTF-8 reconfiguration for Windows compatibility."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_stdout.reconfigure = MagicMock()

        prepare_server_display()

        # Should attempt to reconfigure stdout
        mock_stdout.reconfigure.assert_called_once_with(
            encoding="utf-8", errors="replace"
        )

    @patch("bindu.utils.display.Console")
    @patch("sys.stdout")
    def test_utf8_reconfigure_failure_handled(self, mock_stdout, mock_console_class):
        """Test that UTF-8 reconfigure failures are handled gracefully."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console
        mock_stdout.reconfigure = MagicMock(side_effect=Exception("Reconfigure failed"))

        # Should not raise exception
        prepare_server_display()

        # Should still create display
        assert mock_console.print.call_count > 0

    @patch("bindu.utils.display.Console")
    def test_display_endpoints_with_tunnel(self, mock_console_class):
        """Test that endpoints use tunnel URL when available."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        prepare_server_display(
            host="localhost", port=3773, tunnel_url="https://tunnel.example.com"
        )

        # Verify endpoints use tunnel URL
        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any(
            "tunnel.example.com" in str(call) and "agent.json" in str(call)
            for call in calls
        )

    @patch("bindu.utils.display.Console")
    def test_display_endpoints_without_tunnel(self, mock_console_class):
        """Test that endpoints use local URL when tunnel not available."""
        mock_console = MagicMock()
        mock_console_class.return_value = mock_console

        prepare_server_display(host="localhost", port=3773)

        # Verify endpoints use local URL
        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any(
            "localhost:3773" in str(call) and "agent.json" in str(call)
            for call in calls
        )
