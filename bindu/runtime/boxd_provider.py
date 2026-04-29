"""BoxdRuntimeProvider — runs a bindu agent inside a boxd microVM.

Two modes:

- **A2** (default): ship local source via tar+gzip, install deps in the VM,
  exec ``bindu serve --script <agent>``.
- **A1**: provide an ``image`` field; boxd creates the VM from that image
  and the image's CMD is the entry point. No source ship.

The host's role ends after the agent is healthy. A2A clients then talk
directly to the VM's public URL.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, AsyncIterator, Literal

import httpx

from bindu.runtime.base import RuntimeHandle, RuntimeProvider, register_provider
from bindu.runtime.config import RuntimeConfig
from bindu.runtime.source_packager import build_tarball


def _make_compute(**kwargs: Any):
    """Construct a boxd Compute client.

    Indirection so tests can monkey-patch in a fake Compute.

    Workaround: the boxd Python SDK currently uses TLS for any non-localhost
    host, but production gRPC at ``boxd.sh:9443`` is plaintext (matches what
    ``boxd-cli`` does). When ``BOXD_INSECURE=1`` is set, we replace the SDK's
    channel construction with an ``insecure_channel``. Remove once the SDK
    natively supports plaintext for production.
    """
    from boxd.aio import Compute

    compute = Compute(**kwargs)

    if os.environ.get("BOXD_INSECURE") == "1":
        import grpc
        import grpc.aio

        from boxd._generated import api_pb2_grpc

        async def _insecure_ensure_channel():
            if compute._stub is not None:
                return compute._stub
            interceptor = compute._auth.interceptor()
            channel = grpc.aio.insecure_channel(
                compute._api_url,
                interceptors=[interceptor],
            )
            compute._channel = channel
            compute._stub = api_pb2_grpc.BoxdApiStub(channel)
            return compute._stub

        compute._ensure_channel = _insecure_ensure_channel

    return compute


# The bindu default HTTP port. The boxd proxy is configured at VM creation
# to forward the public default proxy at this port. Without this, the
# proxy default (port 8000) does not match bindu's default (3773) and the
# agent's public URL is unreachable.
BINDU_DEFAULT_PORT = 3773

# Where we stage the user's source inside the VM. Must be writable by the
# default VM user (``boxd``). ``/app`` is not writable without sudo on
# stock boxd images, so we use the user's home directory.
APP_DIR = "/home/boxd/app"


class BoxdRuntimeProvider(RuntimeProvider):
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
            lifecycle=LifecycleConfig(
                auto_suspend_timeout=config.auto_suspend,
            ),
            network=NetworkConfig(
                proxies=[ProxyEntry(name="", port=BINDU_DEFAULT_PORT)],
            ),
        )
        create_kwargs: dict[str, Any] = {
            "name": name,
            "config": box_config,
        }
        if config.image:
            create_kwargs["image"] = config.image
        return await compute.box.create(**create_kwargs)

    async def _wait_vm_ready(self, box: Any, timeout: float = 60.0) -> None:
        """Wait until the VM's in-VM exec server is responsive.

        ``box.create()`` returns once the VM is "running", but the takeoff
        agent inside the VM (which serves exec/write_file) takes a few more
        seconds. Poll with a trivial exec until it responds or we time out.
        """
        from boxd.errors import BoxdError

        deadline = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < deadline:
            try:
                result = await box.exec("true")
                if getattr(result, "exit_code", 0) == 0:
                    return
            except BoxdError:
                pass
            await asyncio.sleep(2.0)
        raise TimeoutError(f"VM {box.name} did not become exec-ready within {timeout}s")

    async def _ship_source(self, box: Any, source_dir: Path) -> None:
        """Tar+gzip ``source_dir``, upload, extract to ``APP_DIR`` in the VM."""
        blob = build_tarball(source_dir)
        await box.write_file(blob, "/tmp/source.tar.gz")
        mkdir = await box.exec("mkdir", "-p", APP_DIR)
        if getattr(mkdir, "exit_code", 0) != 0:
            stderr = getattr(mkdir, "stderr", "")
            raise RuntimeError(f"failed to mkdir {APP_DIR}: {stderr}")
        result = await box.exec("tar", "xzf", "/tmp/source.tar.gz", "-C", APP_DIR)
        if getattr(result, "exit_code", 0) != 0:
            stderr = getattr(result, "stderr", "")
            raise RuntimeError(f"failed to extract source in VM: {stderr}")

    async def _install_deps(
        self,
        box: Any,
        has_pyproject: bool,
        has_requirements: bool,
        bindu_version: str | None = None,
    ) -> None:
        """Install bindu + the user's deps inside the VM (in APP_DIR).

        Uses ``--break-system-packages`` because the boxd default image is
        Ubuntu 24.04, where the system Python is "externally managed" (PEP
        668) and ``pip install`` is refused without that flag. Acceptable
        here because the VM is single-tenant and dedicated to the agent.
        """
        bindu_pkg = f"bindu=={bindu_version}" if bindu_version else "bindu"
        pip = ("pip", "install", "--break-system-packages")
        commands: list[tuple[str, ...]] = [(*pip, bindu_pkg)]
        if has_requirements:
            commands.append((*pip, "-r", f"{APP_DIR}/requirements.txt"))
        if has_pyproject:
            commands.append(
                (
                    "sh",
                    "-c",
                    f"cd {APP_DIR} && pip install --break-system-packages -e .",
                )
            )
        for cmd in commands:
            result = await box.exec(*cmd)
            if getattr(result, "exit_code", 0) != 0:
                stderr = getattr(result, "stderr", "")
                raise RuntimeError(f"command {cmd} failed in VM: {stderr}")

    async def _start_agent(
        self,
        box: Any,
        script: str,
        env: dict[str, str] | None = None,
        public_url: str | None = None,
    ) -> None:
        """Exec ``bindu serve --script /app/<script>`` inside the VM."""
        merged_env = dict(env or {})
        if public_url:
            merged_env["BINDU_PUBLIC_URL"] = public_url

        # nohup + & via sh -c so the exec call returns once the agent is
        # forked. Output captured to a fixed log path; we pipe it via
        # box.stream_logs() later.
        #
        # We invoke ``python <script>`` directly rather than ``bindu serve
        # --script ...``: published bindu wheels don't always ship the
        # console-script entry point, and the user's script calls bindufy()
        # itself, so the CLI shim isn't needed in-VM.
        cmd_str = (
            f"cd {APP_DIR} && nohup python3 {APP_DIR}/{script} "
            f"> /tmp/bindu-agent.log 2>&1 &"
        )
        result = await box.exec("sh", "-c", cmd_str, env=merged_env)
        if getattr(result, "exit_code", 0) != 0:
            stderr = getattr(result, "stderr", "")
            raise RuntimeError(f"failed to start agent: {stderr}")

    async def _wait_healthy(self, url: str, timeout: float = 60.0) -> None:
        """Poll ``{url}/health`` until 200 or timeout."""
        deadline = asyncio.get_event_loop().time() + timeout
        async with httpx.AsyncClient(timeout=5.0) as client:
            while asyncio.get_event_loop().time() < deadline:
                try:
                    resp = await client.get(f"{url}/health")
                    if resp.status_code == 200:
                        return
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(1.0)
        raise TimeoutError(f"agent at {url} did not become healthy within {timeout}s")

    @staticmethod
    def _detect_script_name(source_dir: Path) -> str:
        """Pick the agent's entry script.

        Prefers a top-level ``.py`` file that calls ``bindufy(``. Falls back
        to the first ``.py`` file in alphabetical order.
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
        if not (os.environ.get("BOXD_API_KEY") or os.environ.get("BOXD_TOKEN")):
            raise RuntimeError(
                "BOXD_API_KEY or BOXD_TOKEN must be set in the host environment"
            )

        async with _make_compute() as compute:
            box = await self._resolve_vm(compute, agent_name, config)
            # The boxd SDK returns box.url with or without a scheme depending
            # on the underlying RPC (CreateVm includes it; GetVm may not).
            # Normalize.
            raw_url = box.url or f"{agent_name}.boxd.sh"
            if not raw_url.startswith(("http://", "https://")):
                raw_url = f"https://{raw_url}"
            public_url = raw_url

            # The VM may report "running" before its in-VM exec server is
            # responsive. Wait until exec works before shipping anything.
            await self._wait_vm_ready(box, timeout=60.0)

            # Force the default proxy at bindu's port. `_resolve_vm` sets
            # this at creation, but if the VM was created before we
            # introduced that wiring (or by another path), the proxy may
            # still be on its boxd default of 8000. Idempotent on warm runs.
            try:
                await box.set_proxy_port(port=BINDU_DEFAULT_PORT)
            except AttributeError:
                # Older boxd SDK without set_proxy_port — non-fatal; cold
                # path's create-time NetworkConfig still applies.
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
            # else: A1 — image's CMD already starts the agent.

            await self._wait_healthy(public_url, timeout=60.0)

            return RuntimeHandle(
                name=agent_name,
                url=public_url,
                provider="boxd",
                metadata={
                    "vm_id": box.id,
                    "public_ip": box.public_ip,
                },
            )

    async def health(self, handle: RuntimeHandle) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{handle.url}/health")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def stream_logs(
        self, handle: RuntimeHandle, follow: bool = True
    ) -> AsyncIterator[bytes]:
        async with _make_compute() as compute:
            box = await compute.box.get(handle.name)
            async for chunk in box.stream_logs(follow=follow):
                yield chunk

    async def on_exit(
        self,
        handle: RuntimeHandle,
        mode: Literal["suspend", "destroy", "detach"],
    ) -> None:
        if mode == "detach":
            return
        async with _make_compute() as compute:
            try:
                box = await compute.box.get(handle.name)
            except Exception:
                return
            if mode == "destroy":
                await box.destroy()
            # mode == "suspend": rely on boxd's auto_suspend_timeout (set
            # at create time). Nothing to do here.


register_provider("boxd", BoxdRuntimeProvider)
