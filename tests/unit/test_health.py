from types import SimpleNamespace
from unittest.mock import AsyncMock
from starlette.testclient import TestClient
from bindu.server.applications import BinduApplication


def make_minimal_manifest():
    """
    Return a minimal manifest-like object that satisfies the
    parts of code that check manifest.capabilities and manifest.url/name.
    """
    return SimpleNamespace(
        capabilities={"extensions": []},
        url="http://localhost:3773",
        name="test_agent",
    )


def make_dummy_task_manager():
    """
    Return a minimal dummy TaskManager-like object with the attributes
    BinduApplication checks at request time.
    """
    # The app checks `task_manager is None or not task_manager.is_running`
    return SimpleNamespace(is_running=True)


def test_health_endpoint_ok():
    # Provide a minimal manifest so BinduApplication doesn't try to access attributes on None
    manifest = make_minimal_manifest()
    app = BinduApplication(manifest=manifest, debug=True)

    # Stub a minimal TaskManager so the app will accept requests in tests.
    app.task_manager = make_dummy_task_manager()

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert isinstance(body["uptime_seconds"], (int, float))
    assert "version" in body
    assert body["ready"] is True


def test_health_endpoint_includes_scheduler_health():
    """Test that scheduler health is included when scheduler supports get_health_status."""
    manifest = make_minimal_manifest()
    app = BinduApplication(manifest=manifest, debug=True)
    app.task_manager = make_dummy_task_manager()

    # Mock a scheduler with get_health_status
    mock_scheduler = SimpleNamespace(
        get_health_status=AsyncMock(return_value={
            "healthy": True,
            "consecutive_errors": 0,
            "backoff_active": False,
            "current_backoff_delay": None,
            "status": "healthy",
        }),
    )
    app._scheduler = mock_scheduler
    app._storage = SimpleNamespace()  # Needs to be non-None for strict_ready

    client = TestClient(app)
    resp = client.get("/health")
    body = resp.json()

    assert "scheduler" in body
    assert body["scheduler"]["status"] == "healthy"
    assert body["scheduler"]["consecutive_errors"] == 0
    assert body["health"] == "healthy"


def test_health_endpoint_reflects_scheduler_degradation():
    """Test that overall health reflects scheduler degradation."""
    manifest = make_minimal_manifest()
    app = BinduApplication(manifest=manifest, debug=True)
    app.task_manager = make_dummy_task_manager()

    mock_scheduler = SimpleNamespace(
        get_health_status=AsyncMock(return_value={
            "healthy": True,
            "consecutive_errors": 7,
            "backoff_active": True,
            "current_backoff_delay": 6.4,
            "status": "degraded",
        }),
    )
    app._scheduler = mock_scheduler
    app._storage = SimpleNamespace()

    client = TestClient(app)
    resp = client.get("/health")
    body = resp.json()

    assert body["scheduler"]["status"] == "degraded"
    assert body["scheduler"]["backoff_active"] is True
    assert body["health"] == "degraded"


def test_health_endpoint_reflects_scheduler_unavailable():
    """Test that overall health reflects scheduler unavailable status."""
    manifest = make_minimal_manifest()
    app = BinduApplication(manifest=manifest, debug=True)
    app.task_manager = make_dummy_task_manager()

    mock_scheduler = SimpleNamespace(
        get_health_status=AsyncMock(return_value={
            "healthy": False,
            "consecutive_errors": 0,
            "backoff_active": False,
            "current_backoff_delay": None,
            "status": "unavailable",
        }),
    )
    app._scheduler = mock_scheduler
    app._storage = SimpleNamespace()

    client = TestClient(app)
    resp = client.get("/health")
    body = resp.json()

    assert body["scheduler"]["status"] == "unavailable"
    assert body["health"] == "degraded"


def test_health_endpoint_no_scheduler_section_for_memory():
    """Test that scheduler section is absent when scheduler lacks get_health_status."""
    manifest = make_minimal_manifest()
    app = BinduApplication(manifest=manifest, debug=True)
    app.task_manager = make_dummy_task_manager()

    # InMemoryScheduler-like object without get_health_status
    app._scheduler = SimpleNamespace()

    client = TestClient(app)
    resp = client.get("/health")
    body = resp.json()

    assert "scheduler" not in body
