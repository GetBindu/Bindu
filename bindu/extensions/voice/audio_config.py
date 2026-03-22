"""Audio format constants and validation for the voice extension.

Standard speech processing format used across the pipeline:
PCM 16-bit signed little-endian, 16kHz, mono.
"""

# Standard speech processing format
DEFAULT_SAMPLE_RATE: int = 16000
DEFAULT_CHANNELS: int = 1
DEFAULT_ENCODING: str = "linear16"  # PCM 16-bit signed little-endian
BYTES_PER_SAMPLE: int = 2

# Frame sizing for real-time streaming
FRAME_DURATION_MS: int = 20  # 20ms frames
FRAME_SIZE: int = DEFAULT_SAMPLE_RATE * FRAME_DURATION_MS // 1000 * BYTES_PER_SAMPLE  # 640 bytes

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
