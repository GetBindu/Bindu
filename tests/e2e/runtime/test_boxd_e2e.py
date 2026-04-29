"""Real-boxd-VM e2e for the runtime provider.

Skipped unless ``BOXD_E2E=1`` and ``BOXD_API_KEY`` (or ``BOXD_TOKEN``) is set.
This test creates a real VM, ships a tiny echo agent, hits the A2A endpoint,
and destroys the VM. Slow (~30–60s), costs real boxd resources.
"""
import os
from pathlib import Path

import httpx
import pytest

from bindu.runtime import RuntimeConfig
from bindu.runtime.boxd_provider import BoxdRuntimeProvider

pytestmark = [
    pytest.mark.boxd_e2e,
    pytest.mark.skipif(
        os.environ.get("BOXD_E2E") != "1",
        reason="set BOXD_E2E=1 to enable",
    ),
    pytest.mark.skipif(
        not (os.environ.get("BOXD_API_KEY") or os.environ.get("BOXD_TOKEN")),
        reason="BOXD_API_KEY or BOXD_TOKEN required",
    ),
]


@pytest.mark.asyncio
async def test_full_lifecycle(tmp_path):
    """Deploy → A2A request → assert echo → destroy."""
    fixture_src = Path(__file__).parent / "echo_agent.py"
    (tmp_path / "echo_agent.py").write_text(fixture_src.read_text())
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "boxd-e2e-echo"\nversion = "0.1.0"\n'
    )

    p = BoxdRuntimeProvider()
    cfg = RuntimeConfig.from_dict(
        {
            "provider": "boxd",
            "auto_suspend": 30,
        }
    )

    handle = None
    try:
        handle = await p.deploy(
            agent_name="boxd-e2e-echo",
            source_dir=tmp_path,
            config=cfg,
        )
        assert handle.url

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                handle.url + "/",
                json={
                    "jsonrpc": "2.0",
                    "id": "1",
                    "method": "message/send",
                    "params": {
                        "message": {"role": "user", "content": "ping"},
                    },
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert "ping" in str(data)
    finally:
        if handle is not None:
            await p.on_exit(handle, "destroy")
