"""Board configuration loading and validation."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

REQUIRED_FIELDS: tuple[str, ...] = (
    "board_name",
    "serial_port",
    "baud_rate",
    "flash_tool",
    "swd_interface",
    "boot_marker",
    "flash_address",
    "timeout_sec",
    "programmer_cli",
)


class ConfigError(ValueError):
    """Raised when a board config file is missing or malformed."""


@dataclass
class BoardConfig:
    """Typed representation of a board YAML config."""

    board_name: str
    serial_port: str
    baud_rate: int
    flash_tool: str
    swd_interface: str
    boot_marker: str
    flash_address: str
    timeout_sec: int
    programmer_cli: str
    # Absorb any extra fields future configs may carry.
    extras: dict[str, Any] = field(default_factory=dict, repr=False)

    # ------------------------------------------------------------------ #
    # Constructors
    # ------------------------------------------------------------------ #

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoardConfig":
        """Build a BoardConfig from a raw mapping (e.g., parsed YAML)."""
        missing = [f for f in REQUIRED_FIELDS if f not in data]
        if missing:
            raise ConfigError(
                f"Board config is missing required field(s): {', '.join(missing)}"
            )
        known = {f: data[f] for f in REQUIRED_FIELDS}
        extras = {k: v for k, v in data.items() if k not in REQUIRED_FIELDS}
        instance = cls(**known, extras=extras)
        _validate_config(instance)
        return instance

    @classmethod
    def from_file(cls, path: str | Path) -> "BoardConfig":
        """Load and validate a board config from a YAML file."""
        config_path = Path(path)
        if not config_path.exists():
            raise ConfigError(f"Config file not found: {config_path}")
        if not config_path.is_file():
            raise ConfigError(f"Config path is not a file: {config_path}")

        try:
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise ConfigError(f"Failed to parse YAML in {config_path}: {exc}") from exc

        if not isinstance(raw, dict):
            raise ConfigError(
                f"Config file {config_path} must contain a YAML mapping at the top level."
            )

        logger.debug("Loaded config from %s: %s", config_path, raw)
        return cls.from_dict(raw)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def as_dict(self) -> dict[str, Any]:
        """Return a plain dict representation (useful for reports)."""
        return {
            "board_name": self.board_name,
            "serial_port": self.serial_port,
            "baud_rate": self.baud_rate,
            "flash_tool": self.flash_tool,
            "swd_interface": self.swd_interface,
            "boot_marker": self.boot_marker,
            "flash_address": self.flash_address,
            "timeout_sec": self.timeout_sec,
            "programmer_cli": self.programmer_cli,
            **self.extras,
        }


def _validate_config(cfg: BoardConfig) -> None:
    """Additional semantic validation beyond field presence."""
    if cfg.baud_rate <= 0:
        raise ConfigError(f"baud_rate must be positive, got {cfg.baud_rate}")
    if cfg.timeout_sec <= 0:
        raise ConfigError(f"timeout_sec must be positive, got {cfg.timeout_sec}")
    if not cfg.boot_marker.strip():
        raise ConfigError("boot_marker must not be empty or whitespace.")
    if not cfg.flash_address.startswith("0x"):
        raise ConfigError(
            f"flash_address should be a hex string like '0x08000000', got {cfg.flash_address!r}"
        )
