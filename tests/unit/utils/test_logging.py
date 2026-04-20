"""Tests for logging utilities."""

from bindu.utils.logging import get_logger, configure_logger


class TestLogging:
    """Test logging utility functions."""

    def test_get_logger_returns_logger(self):
        """Test getting a logger returns a loguru logger."""
        logger = get_logger("test_module")

        # Loguru logger has specific methods
        assert hasattr(logger, "info")
        assert hasattr(logger, "debug")
        assert hasattr(logger, "error")

    def test_get_logger_with_different_names(self):
        """Test getting loggers with different names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        # Both should be valid loggers
        assert hasattr(logger1, "info")
        assert hasattr(logger2, "info")

    def test_configure_logger_basic(self):
        """Test basic logger configuration."""
        # Should not raise error
        configure_logger()

    def test_configure_logger_docker_mode(self):
        """Test logger configuration in docker mode."""
        # Should not raise error
        configure_logger(docker_mode=True)

    def test_configure_logger_with_log_level(self):
        """Test logger configuration with custom log level."""
        # Should not raise error
        configure_logger(log_level="DEBUG")
