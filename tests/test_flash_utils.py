"""Tests for restore_tools_lab.flash_utils."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from restore_tools_lab.config import BoardConfig
from restore_tools_lab.flash_utils import (
    FlashError,
    FlashResult,
    build_flash_command,
    flash_image,
)

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

VALID_DATA = {
    "board_name": "nucleo_f411re",
    "serial_port": "/dev/ttyUSB0",
    "baud_rate": 115200,
    "flash_tool": "STM32CubeProgrammer",
    "swd_interface": "STLINK",
    "boot_marker": "BOOT_OK",
    "flash_address": "0x08000000",
    "timeout_sec": 20,
    "programmer_cli": "STM32_Programmer_CLI",
}


def make_cfg(**overrides) -> BoardConfig:
    return BoardConfig.from_dict({**VALID_DATA, **overrides})


def make_image(tmp_path: Path, name: str = "blink.bin") -> Path:
    p = tmp_path / name
    p.write_bytes(b"\x00" * 256)
    return p


# --------------------------------------------------------------------------- #
# build_flash_command
# --------------------------------------------------------------------------- #


def test_build_flash_command_contains_cli():
    cfg = make_cfg()
    cmd = build_flash_command(cfg, "/tmp/blink.bin")
    assert cmd[0] == "STM32_Programmer_CLI"


def test_build_flash_command_contains_image():
    cfg = make_cfg()
    cmd = build_flash_command(cfg, "/tmp/blink.bin")
    assert "/tmp/blink.bin" in cmd


def test_build_flash_command_contains_address():
    cfg = make_cfg()
    cmd = build_flash_command(cfg, "/tmp/blink.bin")
    assert "0x08000000" in cmd


def test_build_flash_command_contains_reset():
    cfg = make_cfg()
    cmd = build_flash_command(cfg, "/tmp/blink.bin")
    assert "--reset" in cmd


def test_build_flash_command_contains_verify():
    cfg = make_cfg()
    cmd = build_flash_command(cfg, "/tmp/blink.bin")
    assert "--verify" in cmd


def test_build_flash_command_bl475():
    """BL475 board produces the same shape of command."""
    cfg = make_cfg(board_name="bl475e_iot01a", serial_port="/dev/tty.usbserial-BL475")
    cmd = build_flash_command(cfg, "firmware/blink/blink.bin")
    assert cmd[0] == "STM32_Programmer_CLI"
    assert "0x08000000" in cmd


# --------------------------------------------------------------------------- #
# flash_image — dry_run
# --------------------------------------------------------------------------- #


@patch("restore_tools_lab.flash_utils._programmer_available", return_value=True)
def test_flash_image_dry_run_success(mock_avail, tmp_path: Path):
    cfg = make_cfg()
    image = make_image(tmp_path)
    result = flash_image(cfg, image, dry_run=True)
    assert result.success is True
    assert result.returncode == 0
    assert "dry run" in result.stdout


@patch("restore_tools_lab.flash_utils._programmer_available", return_value=True)
def test_flash_image_dry_run_no_subprocess(mock_avail, tmp_path: Path):
    """dry_run must not invoke subprocess.run."""
    cfg = make_cfg()
    image = make_image(tmp_path)
    with patch("subprocess.run") as mock_run:
        flash_image(cfg, image, dry_run=True)
        mock_run.assert_not_called()


# --------------------------------------------------------------------------- #
# flash_image — error paths
# --------------------------------------------------------------------------- #


def test_flash_image_missing_image_raises(tmp_path: Path):
    cfg = make_cfg()
    with pytest.raises(FlashError, match="not found"):
        flash_image(cfg, tmp_path / "ghost.bin")


@patch("restore_tools_lab.flash_utils._programmer_available", return_value=False)
def test_flash_image_cli_not_on_path_raises(mock_avail, tmp_path: Path):
    cfg = make_cfg()
    image = make_image(tmp_path)
    with pytest.raises(FlashError, match="not found on PATH"):
        flash_image(cfg, image)


@patch("restore_tools_lab.flash_utils._programmer_available", return_value=True)
@patch(
    "subprocess.run",
    side_effect=subprocess.TimeoutExpired(cmd="STM32_Programmer_CLI", timeout=20),
)
def test_flash_image_timeout_returns_failure(mock_run, mock_avail, tmp_path: Path):
    cfg = make_cfg()
    image = make_image(tmp_path)
    result = flash_image(cfg, image)
    assert result.success is False
    assert result.returncode == -1
    assert "Timed out" in result.stderr


# --------------------------------------------------------------------------- #
# flash_image — subprocess success / failure
# --------------------------------------------------------------------------- #


def _make_proc(returncode: int, stdout: str = "", stderr: str = "") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


@patch("restore_tools_lab.flash_utils._programmer_available", return_value=True)
@patch("subprocess.run")
def test_flash_image_rc0_is_success(mock_run, mock_avail, tmp_path: Path):
    mock_run.return_value = _make_proc(0, stdout="Flash complete.")
    cfg = make_cfg()
    image = make_image(tmp_path)
    result = flash_image(cfg, image)
    assert result.success is True
    assert result.returncode == 0


@patch("restore_tools_lab.flash_utils._programmer_available", return_value=True)
@patch("subprocess.run")
def test_flash_image_nonzero_rc_is_failure(mock_run, mock_avail, tmp_path: Path):
    mock_run.return_value = _make_proc(1, stderr="Error: SWD connect failed")
    cfg = make_cfg()
    image = make_image(tmp_path)
    result = flash_image(cfg, image)
    assert result.success is False
    assert result.returncode == 1


# --------------------------------------------------------------------------- #
# FlashResult
# --------------------------------------------------------------------------- #


def test_flash_result_str_pass():
    r = FlashResult(True, 0, "ok", "", ["STM32_Programmer_CLI"])
    assert "OK" in str(r)


def test_flash_result_str_fail():
    r = FlashResult(False, 1, "", "err", ["STM32_Programmer_CLI"])
    assert "FAILED" in str(r)
