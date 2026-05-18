"""Tests for the MTLS pydantic settings block."""

from __future__ import annotations

import pytest


class TestMTLSSettingsDefaults:
    def test_disabled_by_default(self) -> None:
        from bindu.settings import app_settings

        # Phase 1 lands the wiring but does not flip the default; existing
        # deployments must be unaffected until they opt in.
        assert app_settings.mtls.enabled is False

    def test_ca_endpoints_point_at_production_host(self) -> None:
        from bindu.settings import app_settings

        assert app_settings.mtls.ca_url == "https://ca.getbindu.com"
        assert app_settings.mtls.ca_root_url == "https://ca.getbindu.com/roots.pem"

    def test_lifecycle_defaults_match_deployment_guide(self) -> None:
        from bindu.settings import app_settings

        assert app_settings.mtls.cert_ttl_hours == 24
        assert app_settings.mtls.renew_before_hours == 8
        assert app_settings.mtls.renew_check_interval_seconds == 3600

    def test_rollout_mode_defaults_to_hybrid(self) -> None:
        from bindu.settings import app_settings

        # mTLS + Hydra both required during the migration window. Flip to
        # "mtls" once every deployed agent is on a cert.
        assert app_settings.mtls.mode == "hybrid"

    def test_oidc_audience_matches_step_ca_client_id(self) -> None:
        from bindu.settings import app_settings

        # The string must match the ``clientID`` field in step-ca's
        # ca-config.json. Changing one without the other 403s every sign
        # request — that's an operator concern, but pin the default here
        # so the symmetry is obvious from a single source of truth.
        assert app_settings.mtls.oidc_audience == "step-ca"

    def test_key_filenames_are_distinct_from_did(self) -> None:
        from bindu.settings import app_settings

        # mTLS files live next to the DID keypair; the filenames must not
        # collide with private.pem / public.pem.
        assert app_settings.mtls.cert_filename != app_settings.did.private_key_filename
        assert app_settings.mtls.key_filename != app_settings.did.private_key_filename
        assert app_settings.mtls.key_filename != app_settings.did.public_key_filename


class TestMTLSSettingsEnvOverride:
    @pytest.mark.parametrize(
        "env_var,attr,value,coerced",
        [
            ("MTLS__ENABLED", "enabled", "true", True),
            (
                "MTLS__CA_URL",
                "ca_url",
                "https://ca.example.com",
                "https://ca.example.com",
            ),
            ("MTLS__CERT_TTL_HOURS", "cert_ttl_hours", "168", 168),
            ("MTLS__MODE", "mode", "mtls", "mtls"),
        ],
    )
    def test_env_var_overrides_default(
        self,
        monkeypatch: pytest.MonkeyPatch,
        env_var: str,
        attr: str,
        value: str,
        coerced,
    ) -> None:
        monkeypatch.setenv(env_var, value)
        # Re-instantiate so the env var is read fresh.
        from bindu.settings import MTLSSettings

        settings = MTLSSettings()
        assert getattr(settings, attr) == coerced
