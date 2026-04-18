"""Tests for server runner utilities."""

import pytest
from unittest.mock import patch, MagicMock
import threading


class TestServerRunner:
    """Test server runner utility functions."""

    def test_setup_signal_handlers_in_main_thread(self):
        """Test setting up signal handlers in main thread."""
        from bindu.utils.server_runner import setup_signal_handlers

        # Should not raise when called in main thread
        # Note: This actually registers signal handlers, so we mock signal.signal
        with patch("signal.signal") as mock_signal:
            setup_signal_handlers()
            # Should have registered two signal handlers (SIGINT and SIGTERM)
            assert mock_signal.call_count == 2

    def test_setup_signal_handlers_not_in_main_thread(self):
        """Test setting up signal handlers in non-main thread."""
        from bindu.utils.server_runner import setup_signal_handlers

        # Create a mock for the current thread
        with patch("bindu.utils.server_runner.threading") as mock_threading:
            mock_threading.current_thread.return_value = MagicMock()  # Not main thread
            mock_threading.main_thread.return_value = MagicMock(name="MainThread")

            # Should skip registration when not in main thread
            with patch("signal.signal") as mock_signal:
                setup_signal_handlers()
                # Should NOT register signal handlers
                mock_signal.assert_not_called()

    def test_run_server(self):
        """Test running server."""
        from bindu.utils.server_runner import run_server
        from unittest.mock import patch

        mock_app = MagicMock()

        with patch("bindu.utils.server_runner.uvicorn") as mock_uvicorn:
            with patch("bindu.utils.server_runner.setup_signal_handlers"):
                # Mock uvicorn.run to avoid actually starting server
                mock_uvicorn.run = MagicMock()

                # Should not raise when called with mocked uvicorn
                run_server(mock_app, "localhost", 8000, display_info=False)

                # Verify uvicorn.run was called
                mock_uvicorn.run.assert_called_once()

    def test_run_server_with_display_info(self):
        """Test running server with display info."""
        from bindu.utils.server_runner import run_server

        mock_app = MagicMock()

        with patch("bindu.utils.server_runner.uvicorn") as mock_uvicorn:
            with patch("bindu.utils.server_runner.setup_signal_handlers"):
                with patch("bindu.utils.server_runner.logger") as mock_logger:
                    mock_uvicorn.run = MagicMock()

                    run_server(mock_app, "localhost", 8000, display_info=True)

                    # Verify logger was called with startup messages
                    assert mock_logger.info.called