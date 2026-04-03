"""Audio format constants and validation for the voice extension.

Standard speech processing format used across the pipeline:
PCM 16-bit signed little-endian, 16kHz, mono.
"""

# Standard speech processing format
DEFAULT_SAMPLE_RATE: int = 16000
DEFAULT_CHANNELS: int = 1
DEFAULT_ENCODING: str = "linear16"  # PCM 16-bit signed little-endian


def get_bytes_per_sample(encoding: str) -> int:
    """Return the bytes per sample for a supported audio encoding."""
    if encoding == "linear16":
        return 2
    if encoding in {"mulaw", "alaw"}:
        return 1
    raise ValueError(f"Unsupported encoding: {encoding}")


# These constants apply to linear16 only.
BYTES_PER_SAMPLE: int = get_bytes_per_sample(DEFAULT_ENCODING)

# Frame sizing for real-time streaming
FRAME_DURATION_MS: int = 20  # 20ms frames
FRAME_SIZE: int = (
    DEFAULT_SAMPLE_RATE * FRAME_DURATION_MS // 1000 * BYTES_PER_SAMPLE
)  # 640 bytes


def get_frame_size(sample_rate: int, duration_ms: int, encoding: str) -> int:
    """Return a frame size in bytes for the given encoding."""
    return sample_rate * duration_ms // 1000 * get_bytes_per_sample(encoding)


# Supported audio encodings
SUPPORTED_ENCODINGS: frozenset[str] = frozenset({"linear16", "mulaw", "alaw"})

# Limits
MIN_SAMPLE_RATE: int = 8000
MAX_SAMPLE_RATE: int = 48000


def validate_sample_rate(rate: int) -> int:
    """Validate and return sample rate."""
    if not MIN_SAMPLE_RATE <= rate <= MAX_SAMPLE_RATE:
        raise ValueError(
            f"Sample rate must be between {MIN_SAMPLE_RATE} and {MAX_SAMPLE_RATE}, got {rate}"
        )
    return rate


def validate_encoding(encoding: str) -> str:
    """Validate and return audio encoding."""
    if encoding not in SUPPORTED_ENCODINGS:
        raise ValueError(
            f"Unsupported encoding '{encoding}'. Must be one of: {sorted(SUPPORTED_ENCODINGS)}"
        )
    return encoding
