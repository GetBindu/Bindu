import os
from unittest.mock import patch
from bindu.utils.config_loader import (
    create_storage_config_from_env,
    create_scheduler_config_from_env,
    create_tunnel_config_from_env,
    create_sentry_config_from_env,
    load_config_from_env,
    create_auth_config_from_env,
    update_auth_settings,
)


def test_create_storage_config_from_env_user_config():
    user_config = {"storage": {"type": "postgres", "postgres_url": "postgres://test"}}
    config = create_storage_config_from_env(user_config)
    assert config.type == "postgres"
    assert config.database_url == "postgres://test"


def test_create_storage_config_from_env_invalid_type():
    user_config = {"storage": {"type": "mysql"}}
    config = create_storage_config_from_env(user_config)
    assert config.type == "memory"


@patch.dict(
    os.environ, {"STORAGE_TYPE": "postgres", "DATABASE_URL": "postgresql://env"}
)
def test_create_storage_config_from_env_env_vars():
    config = create_storage_config_from_env({})
    assert config.type == "postgres"
    assert config.database_url == "postgresql://env"


def test_create_scheduler_config_from_env_user_config():
    user_config = {"scheduler": {"type": "redis", "redis_url": "redis://localhost"}}
    config = create_scheduler_config_from_env(user_config)
    assert config.type == "redis"
    assert config.redis_url == "redis://localhost"


def test_create_scheduler_config_from_env_invalid_type():
    user_config = {"scheduler": {"type": "unknown"}}
    config = create_scheduler_config_from_env(user_config)
    assert config.type == "memory"


@patch.dict(os.environ, {"SCHEDULER_TYPE": "redis", "REDIS_URL": "redis://env"})
def test_create_scheduler_config_from_env_env_vars():
    config = create_scheduler_config_from_env({})
    assert config.type == "redis"
    assert config.redis_url == "redis://env"


def test_create_tunnel_config_from_env_user_config():
    user_config = {"tunnel": {"enabled": True, "subdomain": "test"}}
    config = create_tunnel_config_from_env(user_config)
    assert config.enabled is True
    assert config.subdomain == "test"


@patch.dict(os.environ, {"TUNNEL_ENABLED": "true", "TUNNEL_SUBDOMAIN": "envtest"})
def test_create_tunnel_config_from_env_env_vars():
    config = create_tunnel_config_from_env({})
    assert config.enabled is True
    assert config.subdomain == "envtest"


def test_create_sentry_config_from_env_user_config():
    user_config = {"sentry": {"enabled": True, "dsn": "http://sentry"}}
    config = create_sentry_config_from_env(user_config)
    assert config.enabled is True
    assert config.dsn == "http://sentry"


@patch.dict(os.environ, {"SENTRY_ENABLED": "true", "SENTRY_DSN": "http://envsentry"})
def test_create_sentry_config_from_env_env_vars():
    config = create_sentry_config_from_env({})
    assert config.enabled is True
    assert config.dsn == "http://envsentry"


@patch.dict(
    os.environ,
    {
        "STORAGE_TYPE": "postgres",
        "DATABASE_URL": "db",
        "SCHEDULER_TYPE": "redis",
        "REDIS_URL": "redis",
        "SENTRY_ENABLED": "true",
        "SENTRY_DSN": "dsn",
        "TELEMETRY_ENABLED": "true",
        "OLTP_ENDPOINT": "end",
        "AUTH__ENABLED": "true",
        "AUTH__PROVIDER": "hydra",
        "HYDRA__ADMIN_URL": "admin",
    },
)
def test_load_config_from_env():
    config = load_config_from_env({})
    assert config["storage"]["type"] == "postgres"
    assert config["scheduler"]["type"] == "redis"
    assert config["sentry"]["enabled"] is True
    assert config["telemetry"] is True
    assert config["oltp_endpoint"] == "end"
    assert config["auth"]["enabled"] is True
    assert config["auth"]["provider"] == "hydra"


def test_create_auth_config_from_env():
    config = {"auth": {"enabled": True}}
    assert create_auth_config_from_env(config) == {"enabled": True}


def test_update_auth_settings():
    from bindu.settings import app_settings

    update_auth_settings(
        {"enabled": True, "provider": "hydra", "admin_url": "http://admin"}
    )
    assert app_settings.auth.enabled is True
    assert app_settings.hydra.admin_url == "http://admin"
