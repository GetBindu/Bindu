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

    def test_set_log_level(self):
        """Test setting log level at runtime."""
        from bindu.utils.logging import set_log_level

        # Should not raise error
        set_log_level("INFO")
        set_log_level("DEBUG")
        set_log_level("WARNING")

    def test_pre_configured_logger(self):
        """Test the pre-configured logger."""
        from bindu.utils.logging import log

        assert hasattr(log, "info")
        assert hasattr(log, "debug")
        log.info("Test message")
