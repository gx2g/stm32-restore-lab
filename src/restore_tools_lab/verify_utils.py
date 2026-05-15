"""Verification utilities: check serial output for the expected boot marker."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from restore_tools_lab.config import BoardConfig
from restore_tools_lab.serial_utils import SerialError, wait_for_marker

logger = logging.getLogger(__name__)


class VerifyError(RuntimeError):
    """Raised when verification cannot be attempted (port error, config error, etc.)."""


@dataclass
class VerifyResult:
    """Outcome of a single boot-marker verification run."""

    passed: bool
    board_name: str
    marker: str
    lines_received: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def status(self) -> str:
        return "PASS" if self.passed else "FAIL"

    def __str__(self) -> str:
        return (
            f"VerifyResult[{self.status}] board={self.board_name!r} "
            f"marker={self.marker!r} lines={len(self.lines_received)}"
        )


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


def verify_boot(
    cfg: BoardConfig,
    *,
    timeout_sec: float | None = None,
) -> VerifyResult:
    """
    Open the serial port and confirm the board emits the expected boot marker.

    Args:
        cfg:         Validated BoardConfig for the board under test.
        timeout_sec: Override the wait timeout (default: cfg.timeout_sec).

    Returns:
        VerifyResult indicating pass/fail and the lines that were received.

    Raises:
        VerifyError: If the serial port cannot be opened (wraps SerialError).
    """
    logger.info("[%s] Starting boot verification (marker=%r).", cfg.board_name, cfg.boot_marker)

    try:
        found, lines = wait_for_marker(cfg, timeout_sec=timeout_sec)
    except SerialError as exc:
        logger.error("[%s] Serial error during verify: %s", cfg.board_name, exc)
        raise VerifyError(str(exc)) from exc

    result = VerifyResult(
        passed=found,
        board_name=cfg.board_name,
        marker=cfg.boot_marker,
        lines_received=lines,
    )
    _log_result(result)
    return result


def verify_boot_from_lines(
    cfg: BoardConfig,
    lines: list[str],
) -> VerifyResult:
    """
    Check whether *lines* (already captured) contain the expected boot marker.

    Useful when serial output has already been captured and you want to
    re-evaluate it without opening the port again.

    Args:
        cfg:   Validated BoardConfig (supplies board_name and boot_marker).
        lines: Pre-captured serial output lines.

    Returns:
        VerifyResult.
    """
    found = any(cfg.boot_marker in line for line in lines)
    result = VerifyResult(
        passed=found,
        board_name=cfg.board_name,
        marker=cfg.boot_marker,
        lines_received=lines,
    )
    _log_result(result)
    return result


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _log_result(result: VerifyResult) -> None:
    if result.passed:
        logger.info("[%s] Boot verification PASSED.", result.board_name)
    else:
        logger.warning(
            "[%s] Boot verification FAILED — marker %r not found in %d line(s).",
            result.board_name,
            result.marker,
            len(result.lines_received),
        )
        if result.lines_received:
            logger.debug("Received lines:\n%s", "\n".join(result.lines_received))
