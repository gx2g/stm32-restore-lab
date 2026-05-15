"""Tests for restore_tools_lab.serial_utils."""

from __future__ import annotations

import itertools
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from restore_tools_lab.config import BoardConfig
from restore_tools_lab.serial_utils import (
    CaptureResult,
    SerialError,
    capture_serial,
    wait_for_marker,
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
    "timeout_sec": 5,
    "programmer_cli": "STM32_Programmer_CLI",
}


def make_cfg(**overrides) -> BoardConfig:
    return BoardConfig.from_dict({**VALID_DATA, **overrides})


def _fake_port(lines: list[str]) -> MagicMock:
    """
    Build a mock serial.Serial whose readline() returns encoded lines then
    cycles b'' (simulates a quiet port after all data is sent).

    Using itertools.cycle(b'') after the data avoids StopIteration leaking
    into callers, which Python 3.7+ would convert to RuntimeError (PEP 479).
    """
    encoded = [line.encode("utf-8") for line in lines]
    # Cycle empty bytes so the deadline loop exits cleanly on its own
    side_effects = itertools.chain(encoded, itertools.repeat(b""))
    port = MagicMock()
    port.readline.side_effect = side_effects
    return port


# --------------------------------------------------------------------------- #
# capture_serial
# --------------------------------------------------------------------------- #


@patch("restore_tools_lab.serial_utils._open_port")
def test_capture_serial_returns_lines(mock_open):
    mock_open.return_value = _fake_port(["line1\n", "line2\n", "line3\n"])
    cfg = make_cfg(timeout_sec=1)
    result = capture_serial(cfg, duration_sec=1)
    assert "line1" in result.lines
    assert "line3" in result.lines


@patch("restore_tools_lab.serial_utils._open_port")
def test_capture_serial_strips_line_endings(mock_open):
    mock_open.return_value = _fake_port(["hello\r\n", "world\r\n"])
    cfg = make_cfg(timeout_sec=1)
    result = capture_serial(cfg, duration_sec=1)
    assert "hello" in result.lines
    assert "world" in result.lines


@patch("restore_tools_lab.serial_utils._open_port")
def test_capture_serial_writes_log_file(mock_open, tmp_path: Path):
    mock_open.return_value = _fake_port(["alpha\n", "beta\n"])
    cfg = make_cfg(timeout_sec=1)
    log_path = tmp_path / "capture.log"
    capture_serial(cfg, duration_sec=1, output_path=log_path)
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "alpha" in content
    assert "beta" in content


@patch("restore_tools_lab.serial_utils._open_port", side_effect=Exception("no port"))
def test_capture_serial_open_failure_raises(mock_open):
    cfg = make_cfg()
    with pytest.raises(SerialError):
        capture_serial(cfg, duration_sec=1)


@patch("restore_tools_lab.serial_utils._open_port")
def test_capture_serial_empty_board(mock_open):
    mock_open.return_value = _fake_port([])
    cfg = make_cfg(timeout_sec=1)
    result = capture_serial(cfg, duration_sec=1)
    assert result.lines == []


# --------------------------------------------------------------------------- #
# wait_for_marker
# --------------------------------------------------------------------------- #


@patch("restore_tools_lab.serial_utils._open_port")
def test_wait_for_marker_found(mock_open):
    mock_open.return_value = _fake_port(["Starting...\n", "BOOT_OK\n", "Running\n"])
    cfg = make_cfg()
    found, lines = wait_for_marker(cfg)
    assert found is True
    assert any("BOOT_OK" in line for line in lines)


@patch("restore_tools_lab.serial_utils._open_port")
def test_wait_for_marker_not_found(mock_open):
    mock_open.return_value = _fake_port(["Starting...\n", "Error!\n"])
    cfg = make_cfg(timeout_sec=1)
    found, lines = wait_for_marker(cfg, timeout_sec=1)
    assert found is False
    assert len(lines) >= 2


@patch("restore_tools_lab.serial_utils._open_port")
def test_wait_for_marker_stops_early_when_found(mock_open):
    """Lines after the marker should not be consumed."""
    lines_data = ["init\n", "BOOT_OK\n", "should_not_appear\n"]
    mock_open.return_value = _fake_port(lines_data)
    cfg = make_cfg()
    found, lines = wait_for_marker(cfg)
    assert found is True
    assert "should_not_appear" not in lines


@patch("restore_tools_lab.serial_utils._open_port", side_effect=Exception("port busy"))
def test_wait_for_marker_port_error_raises(mock_open):
    cfg = make_cfg()
    with pytest.raises(SerialError):
        wait_for_marker(cfg)


# --------------------------------------------------------------------------- #
# CaptureResult
# --------------------------------------------------------------------------- #


def test_capture_result_text_property():
    r = CaptureResult(lines=["a", "b", "c"])
    assert r.text == "a\nb\nc"


def test_capture_result_len():
    r = CaptureResult(lines=["x", "y"])
    assert len(r) == 2


# --------------------------------------------------------------------------- #
# Both boards
# --------------------------------------------------------------------------- #


@patch("restore_tools_lab.serial_utils._open_port")
def test_bl475_wait_for_marker(mock_open):
    mock_open.return_value = _fake_port(["boot init\n", "BOOT_OK\n"])
    cfg = make_cfg(
        board_name="bl475e_iot01a",
        serial_port="/dev/tty.usbserial-BL475",
    )
    found, lines = wait_for_marker(cfg)
    assert found is True
