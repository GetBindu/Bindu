"""BoxdRuntimeProvider — runs a bindu agent inside a boxd microVM.

Two modes:

- **A2** (default): ship local source via tar+gzip, install deps in the VM,
  exec the agent script directly.
- **A1**: provide an ``image`` field; boxd creates the VM from that image
  and the image's ``CMD`` is the entry point. No source ship.

The host's role ends after the agent is healthy. A2A clients then talk
directly to the VM's public URL.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, Literal

import httpx

from bindu.runtime.base import RuntimeHandle, RuntimeProvider, register_provider
from bindu.runtime.config import RuntimeConfig
from bindu.runtime.source_packager import build_tarball

# Bindu's default HTTP port. The boxd proxy is configured to forward to
# this port at VM creation time, so the agent's public URL routes correctly.
BINDU_DEFAULT_PORT = 3773

# Where we stage the user's source inside the VM. Must be writable by the
# default VM user (``boxd``); ``/app`` requires sudo on stock boxd images.
APP_DIR = "/home/boxd/app"

_VM_READY_TIMEOUT = 60.0
_HEALTH_TIMEOUT = 60.0
_POLL_INTERVAL = 1.0


def _make_compute(**kwargs: Any):
    """Construct a boxd Compute client. Indirection so tests can patch."""
    from boxd.aio import Compute

    return Compute(**kwargs)


async def _poll_until(
    probe: Callable[[], Awaitable[bool]],
    *,
    timeout: float,
    interval: float = _POLL_INTERVAL,
    error_msg: str,
) -> None:
    """Call ``probe`` repeatedly until it returns True or ``timeout`` elapses."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        try:
            if await probe():
                return
        except Exception:
            pass
        await asyncio.sleep(interval)
    raise TimeoutError(error_msg)


async def _exec_or_raise(
    box: Any, *cmd: str, env: dict[str, str] | None = None, error: str
) -> Any:
    """Run a command in the VM and raise if it exits non-zero."""
    result = await box.exec(*cmd, env=env) if env is not None else await box.exec(*cmd)
    if getattr(result, "exit_code", 0) != 0:
        stderr = getattr(result, "stderr", "")
        raise RuntimeError(f"{error}: {stderr}")
    return result


class BoxdRuntimeProvider(RuntimeProvider):
    """RuntimeProvider that runs the agent inside a boxd microVM."""

    async def _resolve_vm(self, compute: Any, name: str, config: RuntimeConfig) -> Any:
        """Get or create the VM for this agent (idempotent by name)."""
        from boxd import BoxConfig, LifecycleConfig, NetworkConfig, ProxyEntry
        from boxd.errors import NotFoundError

        try:
            return await compute.box.get(name)
        except NotFoundError:
            pass

        box_config = BoxConfig(
            vcpu=config.vcpu,
            memory=config.memory,
            disk=config.disk,
            lifecycle=LifecycleConfig(auto_suspend_timeout=config.auto_suspend),
            network=NetworkConfig(
                proxies=[ProxyEntry(name="", port=BINDU_DEFAULT_PORT)],
            ),
        )
        create_kwargs: dict[str, Any] = {"name": name, "config": box_config}
        if config.image:
            create_kwargs["image"] = config.image
        return await compute.box.create(**create_kwargs)

    async def _wait_vm_ready(
        self, box: Any, timeout: float = _VM_READY_TIMEOUT
    ) -> None:
        """Wait until the VM's in-VM exec server is responsive.

        ``box.create()`` returns at "running", but the takeoff agent serving
        exec/write_file takes a few more seconds to come up.
        """

        async def probe() -> bool:
            result = await box.exec("true")
            return getattr(result, "exit_code", 0) == 0

        await _poll_until(
            probe,
            timeout=timeout,
            interval=2.0,
            error_msg=f"VM {box.name} did not become exec-ready within {timeout}s",
        )

    async def _ship_source(self, box: Any, source_dir: Path) -> None:
        """Tar+gzip ``source_dir``, upload, extract to ``APP_DIR``."""
        blob = build_tarball(source_dir)
        # /tmp inside the VM is fine: the VM is single-tenant, the host is the
        # only writer, and the file is consumed immediately by the next exec.
        await box.write_file(blob, "/tmp/source.tar.gz")  # nosec B108
        await _exec_or_raise(
            box,
            "sh",
            "-c",
            f"mkdir -p {APP_DIR} && tar xzf /tmp/source.tar.gz -C {APP_DIR}",
            error=f"failed to extract source to {APP_DIR}",
        )

    async def _install_deps(
        self,
        box: Any,
        has_pyproject: bool,
        has_requirements: bool,
        bindu_version: str | None = None,
    ) -> None:
        """Install bindu + the user's deps inside the VM (in ``APP_DIR``).

        ``--break-system-packages``: stock boxd images are Ubuntu 24.04
        where the system Python is "externally managed" (PEP 668) and
        plain ``pip install`` is refused. The VM is single-tenant.
        """
        bindu_pkg = f"bindu=={bindu_version}" if bindu_version else "bindu"
        steps = [f"pip install --break-system-packages {bindu_pkg}"]
        if has_requirements:
            steps.append(
                f"pip install --break-system-packages -r {APP_DIR}/requirements.txt"
            )
        if has_pyproject:
            steps.append(f"cd {APP_DIR} && pip install --break-system-packages -e .")
        # One round-trip with `&&` chaining so the first failure short-circuits.
        await _exec_or_raise(
            box,
            "sh",
            "-c",
            " && ".join(steps),
            error="failed to install deps",
        )

    async def _start_agent(
        self,
        box: Any,
        script: str,
        env: dict[str, str] | None = None,
        public_url: str | None = None,
    ) -> None:
        """Start the agent script inside the VM (detached via nohup).

        We invoke ``python3 <script>`` directly: published bindu wheels do
        not always ship the ``bindu`` console-script entry point, and the
        user's script calls ``bindufy()`` itself.
        """
        merged_env = dict(env or {})
        if public_url:
            merged_env["BINDU_PUBLIC_URL"] = public_url

        await _exec_or_raise(
            box,
            "sh",
            "-c",
            (
                f"cd {APP_DIR} && nohup python3 {APP_DIR}/{script} "
                f"> /tmp/bindu-agent.log 2>&1 &"
            ),
            env=merged_env,
            error="failed to start agent",
        )

    async def _wait_healthy(self, url: str, timeout: float = _HEALTH_TIMEOUT) -> None:
        async with httpx.AsyncClient(timeout=5.0) as client:

            async def probe() -> bool:
                resp = await client.get(f"{url}/health")
                return resp.status_code == 200

            await _poll_until(
                probe,
                timeout=timeout,
                interval=_POLL_INTERVAL,
                error_msg=f"agent at {url} did not become healthy within {timeout}s",
            )

    @staticmethod
    def _detect_script_name(source_dir: Path) -> str:
        """Pick the agent's entry script.

        Prefers a top-level ``.py`` file that calls ``bindufy(``.
        """
        candidates = sorted(source_dir.glob("*.py"))
        for c in candidates:
            try:
                if "bindufy(" in c.read_text(errors="ignore"):
                    return c.name
            except OSError:
                continue
        if candidates:
            return candidates[0].name
        raise RuntimeError(
            f"no .py file found in {source_dir} to use as agent entry point"
        )

    async def deploy(
        self,
        agent_name: str,
        source_dir: Path | None,
        config: RuntimeConfig,
        env: dict[str, str] | None = None,
    ) -> RuntimeHandle:
        """Resolve the VM, ship source (A2) or use image (A1), start agent, wait healthy."""
        if not (os.environ.get("BOXD_API_KEY") or os.environ.get("BOXD_TOKEN")):
            raise RuntimeError(
                "BOXD_API_KEY or BOXD_TOKEN must be set in the host environment"
            )

        async with _make_compute() as compute:
            box = await self._resolve_vm(compute, agent_name, config)
            # box.url is returned with scheme on CreateVm but bare on GetVm.
            raw_url = box.url or f"{agent_name}.boxd.sh"
            if not raw_url.startswith(("http://", "https://")):
                raw_url = f"https://{raw_url}"
            public_url = raw_url

            await self._wait_vm_ready(box, timeout=_VM_READY_TIMEOUT)

            # Refresh proxy port at every deploy: warm runs may have been
            # created before BINDU_DEFAULT_PORT was wired; idempotent.
            try:
                await box.set_proxy_port(port=BINDU_DEFAULT_PORT)
            except AttributeError:
                pass

            if config.image is None:
                if source_dir is None:
                    raise RuntimeError(
                        "source_dir is required when config.image is not set"
                    )
                await self._ship_source(box, source_dir)
                has_pyproject = (source_dir / "pyproject.toml").exists()
                has_requirements = (source_dir / "requirements.txt").exists()
                await self._install_deps(
                    box,
                    has_pyproject=has_pyproject,
                    has_requirements=has_requirements,
                    bindu_version=config.bindu_version,
                )
                script = self._detect_script_name(source_dir)
                merged_env = {**config.env, **(env or {})}
                await self._start_agent(
                    box,
                    script=script,
                    env=merged_env,
                    public_url=public_url,
                )

            await self._wait_healthy(public_url, timeout=_HEALTH_TIMEOUT)

            return RuntimeHandle(
                name=agent_name,
                url=public_url,
                provider="boxd",
                metadata={"vm_id": box.id, "public_ip": box.public_ip},
            )

    async def health(self, handle: RuntimeHandle) -> bool:
        """Return True if the agent's ``/health`` endpoint returns 200."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{handle.url}/health")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def stream_logs(
        self, handle: RuntimeHandle, follow: bool = True
    ) -> AsyncIterator[bytes]:
        """Yield log chunks streamed from the VM's console."""
        async with _make_compute() as compute:
            box = await compute.box.get(handle.name)
            async for chunk in box.stream_logs(follow=follow):
                yield chunk

    async def on_exit(
        self,
        handle: RuntimeHandle,
        mode: Literal["suspend", "destroy", "detach"],
    ) -> None:
        """Apply the on-exit policy (``suspend`` / ``destroy`` / ``detach``)."""
        if mode == "detach":
            return
        async with _make_compute() as compute:
            try:
                box = await compute.box.get(handle.name)
            except Exception:
                return
            if mode == "destroy":
                await box.destroy()
            # mode == "suspend": rely on auto_suspend_timeout (set at create).


register_provider("boxd", BoxdRuntimeProvider)
