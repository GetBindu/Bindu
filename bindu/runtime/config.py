"""RuntimeConfig — parses and validates the `runtime=` block in bindufy()."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

KNOWN_PROVIDERS = ("in-process", "boxd")
KNOWN_ON_EXIT = ("suspend", "destroy", "detach")
BOXD_ONLY_KEYS = frozenset(
    {
        "image",
        "vcpu",
        "memory",
        "disk",
        "auto_suspend",
        "on_exit",
        "bindu_version",
        "env",
    }
)
ALL_KEYS = BOXD_ONLY_KEYS | {"provider"}


class RuntimeConfigError(ValueError):
    """Raised on invalid runtime configuration."""


@dataclass(frozen=True)
class RuntimeConfig:
    """Validated runtime configuration for ``bindufy(runtime=...)``."""

    provider: Literal["in-process", "boxd"] = "in-process"
    image: str | None = None
    vcpu: int = 2
    memory: str = "4G"
    disk: str = "20G"
    auto_suspend: int = 60
    on_exit: Literal["suspend", "destroy", "detach"] = "suspend"
    bindu_version: str | None = None
    env: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> RuntimeConfig:
        """Parse and validate a raw runtime config dict."""
        if raw is None:
            return cls()

        unknown = set(raw) - ALL_KEYS
        if unknown:
            raise RuntimeConfigError(f"unknown runtime keys: {sorted(unknown)}")

        provider = raw.get("provider", "in-process")
        if provider not in KNOWN_PROVIDERS:
            raise RuntimeConfigError(
                f"unknown provider {provider!r}; must be one of {KNOWN_PROVIDERS}"
            )

        if provider == "in-process":
            misplaced = set(raw) & BOXD_ONLY_KEYS
            if misplaced:
                raise RuntimeConfigError(
                    f"keys {sorted(misplaced)} require provider='boxd'"
                )
            return cls(provider="in-process")

        on_exit = raw.get("on_exit", "suspend")
        if on_exit not in KNOWN_ON_EXIT:
            raise RuntimeConfigError(
                f"on_exit must be one of {KNOWN_ON_EXIT}, got {on_exit!r}"
            )

        vcpu = int(raw.get("vcpu", 2))
        if vcpu <= 0:
            raise RuntimeConfigError(f"vcpu must be positive, got {vcpu}")

        return cls(
            provider="boxd",
            image=raw.get("image"),
            vcpu=vcpu,
            memory=raw.get("memory", "4G"),
            disk=raw.get("disk", "20G"),
            auto_suspend=int(raw.get("auto_suspend", 60)),
            on_exit=on_exit,
            bindu_version=raw.get("bindu_version"),
            env=dict(raw.get("env", {})),
        )
