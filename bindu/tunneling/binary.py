"""FRP client binary download and management."""

import hashlib
import os
import platform
import stat
from pathlib import Path

import httpx

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.tunneling.binary")

# Platform detection
MACHINE = platform.machine()
if MACHINE == "x86_64":
    MACHINE = "amd64"
elif MACHINE == "aarch64":
    MACHINE = "arm64"

SYSTEM = platform.system().lower()
EXTENSION = ".exe" if os.name == "nt" else ""

# Binary naming
BINARY_REMOTE_NAME = f"frpc_{SYSTEM}_{MACHINE.lower()}"
BINARY_FILENAME = f"{BINARY_REMOTE_NAME}_v{app_settings.tunnel.frpc_version}{EXTENSION}"

# Storage location
BINDU_HOME = Path.home() / ".bindu"
BINARY_FOLDER = BINDU_HOME / "frpc"
BINARY_PATH = BINARY_FOLDER / BINARY_FILENAME

# Download URL - using official FRP releases
BINARY_URL = f"https://github.com/fatedier/frp/releases/download/v{app_settings.tunnel.frpc_version}/frp_{app_settings.tunnel.frpc_version}_{SYSTEM}_{MACHINE.lower()}.tar.gz"

# Checksums for verification (optional - can be expanded)
CHECKSUMS: dict[str, str] = {
    # Add checksums for specific versions if needed
}

CHUNK_SIZE = 8192


def get_binary_path() -> Path:
    """Get the path to the FRP client binary.

    Returns:
        Path to the frpc binary
    """
    return BINARY_PATH


def download_binary(force: bool = False) -> Path:
    """Download the FRP client binary if not already present.

    Args:
        force: Force re-download even if binary exists

    Returns:
        Path to the downloaded binary

    Raises:
        OSError: If platform is incompatible or download fails
        RuntimeError: If checksum verification fails
    """
    if BINARY_PATH.exists() and not force:
        logger.debug(f"FRP client binary already exists at {BINARY_PATH}")
        return BINARY_PATH

    logger.info(f"Downloading FRP client binary for {SYSTEM}_{MACHINE}...")

    # Create directory
    BINARY_FOLDER.mkdir(parents=True, exist_ok=True)

    try:
        # Download the tar.gz archive
        import tarfile
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            archive_path = tmpdir_path / "frp.tar.gz"

            # Download archive
            with httpx.stream(
                "GET", BINARY_URL, timeout=60, follow_redirects=True
            ) as response:
                if response.status_code == 404:
                    raise OSError(
                        f"FRP binary not found for platform {SYSTEM}_{MACHINE}. "
                        f"Please check if your platform is supported or download manually from "
                        f"https://github.com/fatedier/frp/releases"
                    )

                response.raise_for_status()

                with open(archive_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=CHUNK_SIZE):
                        f.write(chunk)

            logger.debug(f"Downloaded archive to {archive_path}")

            # Extract frpc binary from archive
            with tarfile.open(archive_path, "r:gz") as tar:
                # Find frpc binary in archive
                frpc_member = None
                for member in tar.getmembers():
                    if member.name.endswith(f"frpc{EXTENSION}"):
                        frpc_member = member
                        break

                if not frpc_member:
                    raise RuntimeError("Could not find frpc binary in archive")

                # Extract to temp location
                tar.extract(frpc_member, tmpdir_path)
                extracted_path = tmpdir_path / frpc_member.name

                # Move to final location
                import shutil

                shutil.move(str(extracted_path), str(BINARY_PATH))

        # Make executable
        st = os.stat(BINARY_PATH)
        os.chmod(BINARY_PATH, st.st_mode | stat.S_IEXEC)

        logger.info(f"✅ FRP client binary downloaded to {BINARY_PATH}")

        # Verify checksum if available
        if str(BINARY_URL) in CHECKSUMS:
            verify_checksum(BINARY_PATH, CHECKSUMS[str(BINARY_URL)])

        return BINARY_PATH

    except Exception as e:
        logger.error(f"Failed to download FRP client binary: {e}")
        raise


def verify_checksum(binary_path: Path, expected_checksum: str) -> None:
    """Verify the SHA256 checksum of the binary.

    Args:
        binary_path: Path to the binary file
        expected_checksum: Expected SHA256 checksum

    Raises:
        RuntimeError: If checksum doesn't match
    """
    sha256 = hashlib.sha256()

    with open(binary_path, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE * sha256.block_size), b""):
            sha256.update(chunk)

    calculated = sha256.hexdigest()

    if calculated != expected_checksum:
        raise RuntimeError(
            f"Checksum mismatch for {binary_path}. "
            f"Expected: {expected_checksum}, Got: {calculated}"
        )

    logger.debug("Binary checksum verified successfully")
