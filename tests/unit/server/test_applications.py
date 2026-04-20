"""Tests for Bindu application server."""

from unittest.mock import Mock
from uuid import uuid4

from bindu.common.models import (
    StorageConfig,
    SchedulerConfig,
    AgentManifest,
    TelemetryConfig,
    SentryConfig,
)
from bindu.server import applications
from bindu.server.applications import BinduApplication


class TestBinduApplicationModule:
    """Test Bindu application module imports and constants."""

    def test_module_imports(self):
        """Test that the applications module can be imported."""
        assert hasattr(applications, "BinduApplication")
        assert hasattr(applications, "UNKNOWN_AUTH_PROVIDER_ERROR")
        assert hasattr(applications, "TASKMANAGER_NOT_INITIALIZED_ERROR")

    def test_application_constants(self):
        """Test application constants are defined."""
        assert (
            "Unknown authentication provider"
            in applications.UNKNOWN_AUTH_PROVIDER_ERROR
        )
        assert "TaskManager" in applications.TASKMANAGER_NOT_INITIALIZED_ERROR

    def test_bindu_application_class_exists(self):
        """Test that BinduApplication class exists and is callable."""
        assert callable(applications.BinduApplication)
        assert hasattr(applications.BinduApplication, "__init__")

    def test_storage_config_creation(self):
        """Test creating storage configuration."""
        storage_config = StorageConfig(type="memory")

        assert storage_config.type == "memory"

    def test_scheduler_config_creation(self):
        """Test creating scheduler configuration."""
        scheduler_config = SchedulerConfig(type="memory")

        assert scheduler_config.type == "memory"

    def test_uuid_generation(self):
        """Test UUID generation for penguin_id."""
        id1 = uuid4()
        id2 = uuid4()

        assert id1 != id2
        assert isinstance(id1, type(id2))

    def test_storage_config_postgres(self):
        """Test creating PostgreSQL storage configuration."""
        storage_config = StorageConfig(
            type="postgres", database_url="postgresql://localhost/test"
        )

        assert storage_config.type == "postgres"
        assert storage_config.database_url == "postgresql://localhost/test"

    def test_scheduler_config_memory(self):
        """Test creating memory scheduler configuration."""
        scheduler_config = SchedulerConfig(type="memory")

        assert scheduler_config.type == "memory"


class TestBinduApplicationInitialization:
    """Test BinduApplication initialization."""

    def test_init_with_minimal_config(self):
        """Test initialization with minimal configuration."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}

        app = BinduApplication(manifest=mock_manifest)

        assert app.manifest == mock_manifest
        assert app.penguin_id is not None
        assert app.url == "http://localhost"
        assert app.version == "1.0.0"

    def test_init_with_custom_penguin_id(self):
        """Test initialization with custom penguin_id."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}
        custom_id = uuid4()

        app = BinduApplication(manifest=mock_manifest, penguin_id=custom_id)

        assert app.penguin_id == custom_id

    def test_init_with_storage_config(self):
        """Test initialization with storage configuration."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}
        storage_config = StorageConfig(type="memory")

        app = BinduApplication(manifest=mock_manifest, storage_config=storage_config)

        assert app._storage_config == storage_config

    def test_init_with_scheduler_config(self):
        """Test initialization with scheduler configuration."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}
        scheduler_config = SchedulerConfig(type="memory")

        app = BinduApplication(
            manifest=mock_manifest, scheduler_config=scheduler_config
        )

        assert app._scheduler_config == scheduler_config

    def test_init_with_telemetry_config(self):
        """Test initialization with telemetry configuration."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}
        telemetry_config = TelemetryConfig(enabled=True)

        app = BinduApplication(
            manifest=mock_manifest, telemetry_config=telemetry_config
        )

        assert app._telemetry_config == telemetry_config

    def test_init_with_sentry_config(self):
        """Test initialization with Sentry configuration."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}
        sentry_config = SentryConfig(enabled=True, dsn="https://example.com")

        app = BinduApplication(manifest=mock_manifest, sentry_config=sentry_config)

        assert app._sentry_config == sentry_config

    def test_init_with_custom_url_and_port(self):
        """Test initialization with custom URL and port."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}

        app = BinduApplication(
            manifest=mock_manifest, url="https://example.com", port=8080
        )

        assert app.url == "https://example.com"

    def test_init_with_debug_mode(self):
        """Test initialization with debug mode enabled."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}

        app = BinduApplication(manifest=mock_manifest, debug=True)

        assert app.debug is True

    def test_init_with_description(self):
        """Test initialization with custom description."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}

        app = BinduApplication(
            manifest=mock_manifest, description="Test agent description"
        )

        assert app.description == "Test agent description"

    def test_init_with_cors_origins(self):
        """Test initialization with CORS origins."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}
        cors_origins = ["https://example.com", "https://test.com"]

        app = BinduApplication(manifest=mock_manifest, cors_origins=cors_origins)

        assert app is not None

    def test_init_with_auth_enabled(self):
        """Test initialization with authentication enabled."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}

        app = BinduApplication(manifest=mock_manifest, auth_enabled=True)

        assert app is not None

    def test_init_sets_default_input_modes(self):
        """Test that default input modes are set."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}

        app = BinduApplication(manifest=mock_manifest)

        assert "application/json" in app.default_input_modes

    def test_init_task_manager_is_none(self):
        """Test that task_manager is initially None."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}

        app = BinduApplication(manifest=mock_manifest)

        assert app.task_manager is None

    def test_init_storage_is_none(self):
        """Test that storage is initially None."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}

        app = BinduApplication(manifest=mock_manifest)

        assert app._storage is None

    def test_init_scheduler_is_none(self):
        """Test that scheduler is initially None."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}

        app = BinduApplication(manifest=mock_manifest)

        assert app._scheduler is None

    def test_init_payment_sessions_dict(self):
        """Test that payment_sessions is initialized as empty dict."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}

        app = BinduApplication(manifest=mock_manifest)

        assert isinstance(app.payment_sessions, dict)
        assert len(app.payment_sessions) == 0

    def test_init_with_version(self):
        """Test initialization with custom version."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}

        app = BinduApplication(manifest=mock_manifest, version="2.0.0")

        assert app.version == "2.0.0"

    def test_init_auto_generates_penguin_id(self):
        """Test that penguin_id is auto-generated when not provided."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}

        app1 = BinduApplication(manifest=mock_manifest)
        app2 = BinduApplication(manifest=mock_manifest)

        assert app1.penguin_id != app2.penguin_id

    def test_init_with_default_telemetry_config(self):
        """Test that default telemetry config is created when not provided."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}

        app = BinduApplication(manifest=mock_manifest)

        assert isinstance(app._telemetry_config, TelemetryConfig)

    def test_init_with_default_sentry_config(self):
        """Test that default Sentry config is created when not provided."""
        mock_manifest = Mock(spec=AgentManifest)
        mock_manifest.name = "test-agent"
        mock_manifest.capabilities = {}

        app = BinduApplication(manifest=mock_manifest)

        assert isinstance(app._sentry_config, SentryConfig)
