"""Flash utilities: build CLI commands and invoke STM32CubeProgrammer."""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from restore_tools_lab.config import BoardConfig

logger = logging.getLogger(__name__)


class FlashError(RuntimeError):
    """Raised when a flash operation fails."""


@dataclass
class FlashResult:
    """Outcome of a single flash attempt."""

    success: bool
    returncode: int
    stdout: str
    stderr: str
    command: list[str]

    def __str__(self) -> str:
        status = "OK" if self.success else "FAILED"
        return (
            f"FlashResult[{status}] rc={self.returncode} "
            f"cmd={' '.join(self.command)}"
        )


# --------------------------------------------------------------------------- #
# Command builders
# --------------------------------------------------------------------------- #


def build_flash_command(cfg: BoardConfig, image_path: str | Path) -> list[str]:
    """
    Build the STM32_Programmer_CLI argument list for writing a binary image.

    The produced command writes the image at cfg.flash_address, resets the
    MCU after flashing, and uses the SWD interface configured in cfg.

    Args:
        cfg:        Validated BoardConfig for the target board.
        image_path: Path to the .bin firmware image to flash.

    Returns:
        A list of strings suitable for subprocess.run().
    """
    image = Path(image_path)
    return [
        cfg.programmer_cli,
        "--connect",
        f"port=SWD",
        f"mode=UR",
        "--write",
        str(image),
        cfg.flash_address,
        "--verify",
        "--reset",
        "--log",
    ]


# --------------------------------------------------------------------------- #
# Execution
# --------------------------------------------------------------------------- #


def flash_image(
    cfg: BoardConfig,
    image_path: str | Path,
    *,
    dry_run: bool = False,
    timeout: int | None = None,
) -> FlashResult:
    """
    Flash *image_path* to the board described by *cfg*.

    Args:
        cfg:        Validated BoardConfig.
        image_path: Path to the .bin firmware image.
        dry_run:    If True, build the command but do not execute it.
        timeout:    Override the process timeout in seconds (default: cfg.timeout_sec).

    Returns:
        FlashResult with success status, return code, and captured output.

    Raises:
        FlashError: If the image file is not found, the programmer CLI is not
                    on PATH, or the subprocess raises an unexpected exception.
    """
    image = Path(image_path)
    if not image.exists():
        raise FlashError(f"Image file not found: {image}")

    if not _programmer_available(cfg.programmer_cli):
        raise FlashError(
            f"Programmer CLI not found on PATH: {cfg.programmer_cli!r}. "
            "Install STM32CubeProgrammer and ensure it is on PATH."
        )

    cmd = build_flash_command(cfg, image)
    logger.info("[%s] Flash command: %s", cfg.board_name, " ".join(cmd))

    if dry_run:
        logger.info("[%s] dry_run=True — skipping execution.", cfg.board_name)
        return FlashResult(
            success=True,
            returncode=0,
            stdout="(dry run)",
            stderr="",
            command=cmd,
        )

    effective_timeout = timeout if timeout is not None else cfg.timeout_sec

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=effective_timeout,
        )
    except subprocess.TimeoutExpired:
        logger.error(
            "[%s] Flash timed out after %ss.", cfg.board_name, effective_timeout
        )
        return FlashResult(
            success=False,
            returncode=-1,
            stdout="",
            stderr=f"Timed out after {effective_timeout}s",
            command=cmd,
        )
    except Exception as exc:  # noqa: BLE001
        raise FlashError(f"Unexpected error running flash command: {exc}") from exc

    result = FlashResult(
        success=proc.returncode == 0,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        command=cmd,
    )
    _log_result(cfg.board_name, result)
    return result


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #


def _programmer_available(cli_name: str) -> bool:
    """Return True if *cli_name* is discoverable on PATH."""
    return shutil.which(cli_name) is not None


def _log_result(board_name: str, result: FlashResult) -> None:
    if result.success:
        logger.info("[%s] Flash succeeded (rc=0).", board_name)
    else:
        logger.error(
            "[%s] Flash FAILED (rc=%d).\nstdout:\n%s\nstderr:\n%s",
            board_name,
            result.returncode,
            result.stdout,
            result.stderr,
        )
