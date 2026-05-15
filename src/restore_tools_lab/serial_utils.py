"""Serial utilities: open port, capture lines, close cleanly."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

try:
    import serial  # type: ignore[import-untyped]
    from serial import SerialException  # type: ignore[import-untyped]
except ImportError as exc:  # pragma: no cover
    raise ImportError("pyserial is required: pip install pyserial") from exc

from restore_tools_lab.config import BoardConfig

logger = logging.getLogger(__name__)


class SerialError(RuntimeError):
    """Raised when the serial port cannot be opened or becomes unavailable."""


@dataclass
class CaptureResult:
    """Outcome of a serial capture session."""

    lines: list[str] = field(default_factory=list)
    duration_sec: float = 0.0
    port: str = ""
    baud_rate: int = 0

    @property
    def text(self) -> str:
        """Full captured text as a single string."""
        return "\n".join(self.lines)

    def __len__(self) -> int:
        return len(self.lines)


# --------------------------------------------------------------------------- #
# High-level capture
# --------------------------------------------------------------------------- #


def capture_serial(
    cfg: BoardConfig,
    duration_sec: float | None = None,
    *,
    output_path: str | Path | None = None,
) -> CaptureResult:
    """
    Read lines from the board's serial port for *duration_sec* seconds.

    Args:
        cfg:          Validated BoardConfig.
        duration_sec: How long to read (default: cfg.timeout_sec).
        output_path:  If provided, write captured lines to this file.

    Returns:
        CaptureResult with all received lines.

    Raises:
        SerialError: If the port cannot be opened.
    """
    effective_duration = duration_sec if duration_sec is not None else float(cfg.timeout_sec)
    result = CaptureResult(port=cfg.serial_port, baud_rate=cfg.baud_rate)

    logger.info(
        "[%s] Opening %s at %d baud for %.1fs.",
        cfg.board_name,
        cfg.serial_port,
        cfg.baud_rate,
        effective_duration,
    )

    try:
        port = _open_port(cfg)
    except Exception as exc:
        raise SerialError(
            f"Cannot open serial port {cfg.serial_port!r}: {exc}"
        ) from exc

    start = time.monotonic()
    try:
        for line in _read_lines(port, effective_duration):
            stripped = line.rstrip("\r\n")
            result.lines.append(stripped)
            logger.debug("[%s] << %s", cfg.board_name, stripped)
    finally:
        port.close()
        result.duration_sec = time.monotonic() - start

    logger.info(
        "[%s] Capture complete: %d lines in %.1fs.",
        cfg.board_name,
        len(result.lines),
        result.duration_sec,
    )

    if output_path is not None:
        _write_log(result, Path(output_path))

    return result


# --------------------------------------------------------------------------- #
# Boot marker wait (used by verify / cycle)
# --------------------------------------------------------------------------- #


def wait_for_marker(
    cfg: BoardConfig,
    *,
    timeout_sec: float | None = None,
) -> tuple[bool, list[str]]:
    """
    Open the serial port and wait until the boot marker appears or timeout.

    Args:
        cfg:         Validated BoardConfig.
        timeout_sec: Override timeout (default: cfg.timeout_sec).

    Returns:
        Tuple of (marker_found: bool, lines_received: list[str]).

    Raises:
        SerialError: If the port cannot be opened.
    """
    effective_timeout = timeout_sec if timeout_sec is not None else float(cfg.timeout_sec)
    lines: list[str] = []
    marker = cfg.boot_marker

    logger.info(
        "[%s] Waiting for marker %r on %s (timeout=%.1fs).",
        cfg.board_name,
        marker,
        cfg.serial_port,
        effective_timeout,
    )

    try:
        port = _open_port(cfg)
    except Exception as exc:
        raise SerialError(
            f"Cannot open serial port {cfg.serial_port!r}: {exc}"
        ) from exc

    found = False
    start = time.monotonic()
    try:
        deadline = time.monotonic() + effective_timeout
        while time.monotonic() < deadline:
            batch = _read_lines(port, min(1.0, deadline - time.monotonic()))
            for raw_line in batch:
                stripped = raw_line.rstrip("\r\n")
                lines.append(stripped)
                logger.debug("[%s] << %s", cfg.board_name, stripped)
                if marker in stripped:
                    found = True
                    logger.info("[%s] Boot marker found: %r", cfg.board_name, stripped)
                    break
            if found:
                break
    finally:
        port.close()

    elapsed = time.monotonic() - start
    if not found:
        logger.warning(
            "[%s] Boot marker %r NOT found after %.1fs.", cfg.board_name, marker, elapsed
        )

    return found, lines


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _open_port(cfg: BoardConfig) -> "serial.Serial":
    """Open and return a configured serial port."""
    return serial.Serial(
        port=cfg.serial_port,
        baudrate=cfg.baud_rate,
        timeout=1,          # per-read timeout so we can check the wall-clock deadline
        write_timeout=2,
    )


def _read_lines(
    port: "serial.Serial",
    duration_sec: float,
) -> list[str]:
    """
    Read decoded lines from *port* for up to *duration_sec* seconds.

    Returns a plain list so callers can iterate it freely without triggering
    PEP 479 (StopIteration inside a generator becomes RuntimeError in 3.7+).
    The port's per-read timeout (1 s) keeps the loop responsive to the
    wall-clock deadline without hanging forever.
    """
    deadline = time.monotonic() + duration_sec
    lines: list[str] = []
    while time.monotonic() < deadline:
        try:
            raw = port.readline()
        except StopIteration:
            break
        except SerialException as exc:
            logger.error("Serial read error: %s", exc)
            break
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected read error: %s", exc)
            break
        if not raw:
            continue
        try:
            lines.append(raw.decode("utf-8", errors="replace"))
        except Exception:  # noqa: BLE001
            lines.append(repr(raw))
    return lines


def _write_log(result: CaptureResult, path: Path) -> None:
    """Write captured lines to a file, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(result.lines) + "\n", encoding="utf-8")
    logger.info("Serial log written to %s", path)
