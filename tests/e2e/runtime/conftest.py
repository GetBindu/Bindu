"""Test-only patches for the boxd_e2e suite.

Lives here, not in shipping bindu code, because it pokes at the boxd
Python SDK's private channel construction. When the SDK natively
supports plaintext for the production endpoint, delete this file.
"""
from __future__ import annotations

import os
from typing import Any

import pytest


def _patch_compute_insecure(compute: Any) -> None:
    """Replace ``compute._ensure_channel`` with one that uses ``insecure_channel``.

    The boxd Python SDK uses TLS for any non-localhost host, but production
    gRPC at ``boxd.sh:9443`` is plaintext (matches ``boxd-cli`` behavior).
    """
    import grpc
    import grpc.aio

    from boxd._generated import api_pb2_grpc

    async def _insecure_ensure_channel():
        if compute._stub is not None:
            return compute._stub
        channel = grpc.aio.insecure_channel(
            compute._api_url,
            interceptors=[compute._auth.interceptor()],
        )
        compute._channel = channel
        compute._stub = api_pb2_grpc.BoxdApiStub(channel)
        return compute._stub

    compute._ensure_channel = _insecure_ensure_channel


@pytest.fixture(autouse=True)
def _boxd_insecure_workaround(monkeypatch):
    """When ``BOXD_INSECURE=1``, wrap ``_make_compute`` to force plaintext.

    Autouse so it applies to every test in this directory; no-op when
    ``BOXD_INSECURE`` is not set.
    """
    if os.environ.get("BOXD_INSECURE") != "1":
        return

    import bindu.runtime.boxd_provider as bp

    original = bp._make_compute

    def _patched(**kwargs):
        compute = original(**kwargs)
        _patch_compute_insecure(compute)
        return compute

    monkeypatch.setattr(bp, "_make_compute", _patched)
