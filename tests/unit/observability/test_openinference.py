"""Focused tests for OpenInference observability setup."""

from unittest.mock import MagicMock, patch, Mock

from bindu.observability.openinference import (
    _detect_framework,
    _validate_framework_version,
    _get_package_manager,
    _check_missing_packages,
    setup,
)
from bindu.common.models import AgentFrameworkSpec


class TestFrameworkDetection:
    """Test framework detection logic."""

    def test_detect_framework_success(self):
        """Test successful framework detection."""
        installed = {"agno": Mock(version="1.5.2"), "openai": Mock(version="1.70.0")}

        result = _detect_framework(installed)

        # Should detect agno (higher priority than openai)
        assert result is not None
        assert result.framework == "agno"

    def test_detect_framework_not_found(self):
        """Test when no supported framework is installed."""
        installed = {"requests": Mock(version="2.0.0")}

        result = _detect_framework(installed)

        assert result is None

    def test_detect_framework_priority_order(self):
        """Test that agent frameworks are prioritized over LLM providers."""
        installed = {
            "openai": Mock(version="1.70.0"),
            "langchain": Mock(version="0.1.0"),
        }

        result = _detect_framework(installed)

        # Should detect langchain (agent framework) before openai (LLM provider)
        assert result is not None
        assert result.framework == "langchain"


class TestVersionValidation:
    """Test framework version validation."""

    def test_validate_version_meets_requirement(self):
        """Test version that meets minimum requirement."""
        spec = AgentFrameworkSpec("agno", "openinference-instrumentation-agno", "1.5.0")
        installed = {"agno": Mock(version="1.5.2")}

        is_valid, version = _validate_framework_version(spec, installed)

        assert is_valid is True
        assert version == "1.5.2"

    def test_validate_version_below_requirement(self):
        """Test version below minimum requirement."""
        spec = AgentFrameworkSpec("agno", "openinference-instrumentation-agno", "2.0.0")
        installed = {"agno": Mock(version="1.5.2")}

        is_valid, version = _validate_framework_version(spec, installed)

        assert is_valid is False
        assert version == "1.5.2"

    def test_validate_version_exact_match(self):
        """Test version exactly matching requirement."""
        spec = AgentFrameworkSpec(
            "openai", "openinference-instrumentation-openai", "1.69.0"
        )
        installed = {"openai": Mock(version="1.69.0")}

        is_valid, version = _validate_framework_version(spec, installed)

        assert is_valid is True


class TestPackageManager:
    """Test package manager detection."""

    @patch("bindu.observability.openinference.Path")
    def test_detect_uv_with_lock_file(self, mock_path):
        """Test UV detection with uv.lock file."""
        mock_cwd = MagicMock()
        mock_path.cwd.return_value = mock_cwd
        mock_cwd.__truediv__.return_value.exists.side_effect = [True, False]

        result = _get_package_manager()

        assert result == ["uv", "add"]

    @patch("bindu.observability.openinference.Path")
    def test_detect_uv_with_pyproject(self, mock_path):
        """Test UV detection with pyproject.toml."""
        mock_cwd = MagicMock()
        mock_path.cwd.return_value = mock_cwd
        mock_cwd.__truediv__.return_value.exists.side_effect = [False, True]

        result = _get_package_manager()

        assert result == ["uv", "add"]

    @patch("bindu.observability.openinference.Path")
    @patch("bindu.observability.openinference.sys")
    def test_detect_pip_fallback(self, mock_sys, mock_path):
        """Test fallback to pip when UV not detected."""
        mock_sys.executable = "/usr/bin/python"
        mock_cwd = MagicMock()
        mock_path.cwd.return_value = mock_cwd
        mock_cwd.__truediv__.return_value.exists.return_value = False

        result = _get_package_manager()

        assert result == ["/usr/bin/python", "-m", "pip", "install"]


class TestMissingPackages:
    """Test missing package detection."""

    @patch("bindu.observability.openinference.app_settings")
    def test_no_missing_packages(self, mock_settings):
        """Test when all packages are installed."""
        mock_settings.observability.base_packages = ["opentelemetry-api"]
        spec = AgentFrameworkSpec("agno", "openinference-instrumentation-agno", "1.5.0")
        installed = {
            "opentelemetry-api": Mock(),
            "openinference-instrumentation-agno": Mock(),
        }

        missing = _check_missing_packages(spec, installed)

        assert missing == []

    @patch("bindu.observability.openinference.app_settings")
    def test_missing_instrumentation_package(self, mock_settings):
        """Test when instrumentation package is missing."""
        mock_settings.observability.base_packages = ["opentelemetry-api"]
        spec = AgentFrameworkSpec("agno", "openinference-instrumentation-agno", "1.5.0")
        installed = {"opentelemetry-api": Mock()}

        missing = _check_missing_packages(spec, installed)

        assert "openinference-instrumentation-agno" in missing


class TestSetupFunction:
    """Test main setup function."""

    @patch("bindu.observability.openinference._setup_tracer_provider")
    @patch("bindu.observability.openinference.distributions")
    def test_setup_without_framework(self, mock_distributions, mock_tracer):
        """Test setup when no AI framework is installed."""
        mock_distributions.return_value = []
        mock_tracer.return_value = Mock()

        # Should not raise, just skip framework instrumentation
        setup(verbose_logging=True)

        mock_tracer.assert_called_once()

    @patch("bindu.observability.openinference._setup_tracer_provider")
    @patch("bindu.observability.openinference.distributions")
    @patch("bindu.observability.openinference._instrument_framework")
    @patch("bindu.observability.openinference.app_settings")
    def test_setup_with_valid_framework(
        self, mock_settings, mock_instrument, mock_distributions, mock_tracer
    ):
        """Test successful setup with valid framework."""
        mock_settings.observability.base_packages = []
        mock_settings.observability.instrumentor_map = {"agno": ("module", "Class")}

        # Create mock distributions for both framework and instrumentation package
        mock_agno = Mock()
        mock_agno.name = "agno"
        mock_agno.version = "1.5.2"

        mock_instrumentation = Mock()
        mock_instrumentation.name = "openinference-instrumentation-agno"
        mock_instrumentation.version = "1.0.0"

        mock_distributions.return_value = [mock_agno, mock_instrumentation]

        tracer = Mock()
        mock_tracer.return_value = tracer

        setup()

        mock_instrument.assert_called_once_with("agno", tracer)

    @patch("bindu.observability.openinference._setup_tracer_provider")
    @patch("bindu.observability.openinference.distributions")
    def test_setup_with_old_framework_version(self, mock_distributions, mock_tracer):
        """Test setup skips instrumentation for old framework version."""
        mock_dist = Mock()
        mock_dist.name = "agno"
        mock_dist.version = "1.0.0"  # Below minimum 1.5.2
        mock_distributions.return_value = [mock_dist]

        mock_tracer.return_value = Mock()

        # Should not raise, just skip instrumentation
        setup(verbose_logging=True)

    @patch("bindu.observability.openinference._setup_tracer_provider")
    def test_setup_with_multiple_endpoints(self, mock_tracer):
        """Test setup with multiple OTLP endpoints."""
        mock_tracer.return_value = Mock()

        endpoints = [
            "http://localhost:4318/v1/traces",
            "http://localhost:6006/v1/traces",
        ]

        setup(oltp_endpoint=endpoints)

        # Should pass list to tracer provider
        call_kwargs = mock_tracer.call_args[1]
        assert call_kwargs["oltp_endpoint"] == endpoints


class TestSetupEdgeCases:
    """Test edge cases in setup."""

    @patch("bindu.observability.openinference._setup_tracer_provider")
    @patch("bindu.observability.openinference.distributions")
    @patch("bindu.observability.openinference._instrument_framework")
    def test_setup_instrumentation_import_error(
        self, mock_instrument, mock_distributions, mock_tracer
    ):
        """Test graceful handling of instrumentation import errors."""
        mock_dist = Mock()
        mock_dist.name = "agno"
        mock_dist.version = "1.5.2"
        mock_distributions.return_value = [mock_dist]

        mock_tracer.return_value = Mock()
        mock_instrument.side_effect = ImportError("Module not found")

        # Should not raise, just log error
        setup()

    @patch("bindu.observability.openinference._setup_tracer_provider")
    def test_setup_with_custom_service_name(self, mock_tracer):
        """Test setup with custom service name."""
        mock_tracer.return_value = Mock()

        setup(oltp_service_name="my-custom-agent")

        call_kwargs = mock_tracer.call_args[1]
        assert call_kwargs["oltp_service_name"] == "my-custom-agent"
