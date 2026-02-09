"""FRP tunnel implementation."""

import atexit
import re
import subprocess
import time
from pathlib import Path
from typing import Optional

from bindu.settings import app_settings
from bindu.tunneling.binary import download_binary
from bindu.tunneling.config import TunnelConfig
from bindu.utils.logging import get_logger

logger = get_logger("bindu.tunneling.tunnel")

# Global list to track active tunnels for cleanup
ACTIVE_TUNNELS: list["Tunnel"] = []


class Tunnel:
    """Manages an FRP tunnel connection.

    This class handles the lifecycle of an FRP client process that creates
    a tunnel from a local server to a public URL.
    """

    def __init__(self, config: TunnelConfig):
        """Initialize tunnel with configuration.

        Args:
            config: Tunnel configuration
        """
        self.config = config
        self.proc: Optional[subprocess.Popen] = None
        self.public_url: Optional[str] = None
        self._binary_path: Optional[Path] = None

    def start(self) -> str:
        """Start the tunnel and return the public URL.

        Returns:
            Public URL for accessing the tunneled service

        Raises:
            ValueError: If tunnel creation fails
            RuntimeError: If binary download fails
        """
        logger.info("Starting FRP tunnel...")

        # Download binary if needed
        try:
            self._binary_path = download_binary()
        except Exception as e:
            logger.error(f"Failed to download FRP binary: {e}")
            raise RuntimeError(f"Could not download FRP client binary: {e}") from e

        # Start the tunnel process
        self.public_url = self._start_tunnel()

        logger.info(f"✅ Tunnel established: {self.public_url}")
        return self.public_url

    def stop(self) -> None:
        """Stop the tunnel and cleanup the process."""
        if self.proc is not None:
            logger.info(
                f"Stopping tunnel {self.config.local_host}:{self.config.local_port} <> {self.public_url}"
            )
            try:
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(
                    "Tunnel process did not terminate gracefully, killing..."
                )
                self.proc.kill()
            except Exception as e:
                logger.error(f"Error stopping tunnel: {e}")
            finally:
                self.proc = None

    def _start_tunnel(self) -> str:
        """Start the FRP client process and parse the public URL.

        Returns:
            Public URL from the tunnel

        Raises:
            ValueError: If tunnel creation fails or times out
        """
        if not self._binary_path:
            raise RuntimeError("Binary path not set")

        if not self.config.local_port:
            raise ValueError("Local port must be set in tunnel config")

        # Parse server address
        server_host, server_port = self.config.server_address.split(":")

        # Build command - use separate flags for server host and port
        command = [
            str(self._binary_path),
            self.config.protocol,
            "-n",
            "bindu-tunnel",
            "-l",
            str(self.config.local_port),
            "-i",
            self.config.local_host,
            "--uc",  # Use compression
            "--sd",
            self.config.subdomain or "random",
            "--ue",  # Use encryption
            "-s",
            server_host,
            "-P",
            server_port,
            "--disable_log_color",
        ]

        # Add TLS if configured
        if self.config.use_tls:
            command.extend(["--tls_enable"])

        logger.debug(f"Starting FRP client with command: {' '.join(command)}")

        # Start process
        try:
            self.proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except Exception as e:
            raise RuntimeError(f"Failed to start FRP client process: {e}") from e

        # Register cleanup
        ACTIVE_TUNNELS.append(self)
        atexit.register(self.stop)

        # Parse URL from output
        return self._read_url_from_output()

    def _read_url_from_output(self) -> str:
        """Read and parse the public URL from FRP client output.

        Returns:
            Public URL

        Raises:
            ValueError: If URL cannot be parsed or tunnel fails
        """
        start_time = time.time()
        log_lines: list[str] = []
        url = ""

        def raise_tunnel_error() -> None:
            """Raise error with collected logs."""
            log_text = "\n".join(log_lines)
            logger.error(f"Tunnel creation failed:\n{log_text}")
            raise ValueError(f"{app_settings.tunnel.error_message}\n{log_text}")

        if not self.proc or not self.proc.stdout:
            raise RuntimeError("Process not started or stdout not available")

        while not url:
            # Check timeout
            if time.time() - start_time >= app_settings.tunnel.timeout_seconds:
                raise_tunnel_error()

            # Check if process died
            if self.proc.poll() is not None:
                # Process exited, read remaining output
                stderr_output = self.proc.stderr.read() if self.proc.stderr else ""
                if stderr_output:
                    log_lines.append(f"STDERR: {stderr_output}")
                raise_tunnel_error()

            # Read line
            try:
                line = self.proc.stdout.readline()
                if not line:
                    time.sleep(0.1)
                    continue

                line = line.strip()
                if line:
                    log_lines.append(line)
                    logger.debug(f"FRP: {line}")

                # Look for success message
                # FRP output format: "start proxy success" (URL may or may not be included)
                if "start proxy success" in line:
                    # Try to extract URL from line if present
                    match = re.search(r"start proxy success:\s*(.+)", line)
                    if match:
                        url = match.group(1).strip()
                        # Update subdomain if it was auto-generated
                        if not self.config.subdomain:
                            # Extract subdomain from URL
                            subdomain_match = re.search(r"https?://([^.]+)\.", url)
                            if subdomain_match:
                                self.config.subdomain = subdomain_match.group(1)
                    else:
                        # URL not in output, construct it from config
                        url = self.config.get_public_url()
                        logger.info(
                            f"Tunnel started successfully, constructed URL: {url}"
                        )

                # Check for login failure
                elif "login to server failed" in line or "error" in line.lower():
                    raise_tunnel_error()

            except Exception as e:
                if isinstance(e, ValueError):
                    raise
                logger.error(f"Error reading FRP output: {e}")
                raise_tunnel_error()

        return url


def cleanup_tunnels() -> None:
    """Cleanup all active tunnels on exit."""
    for tunnel in ACTIVE_TUNNELS:
        try:
            tunnel.stop()
        except Exception as e:
            logger.error(f"Error cleaning up tunnel: {e}")
    ACTIVE_TUNNELS.clear()


# Register global cleanup
atexit.register(cleanup_tunnels)
