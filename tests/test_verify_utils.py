"""Tests for restore_tools_lab.verify_utils."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from restore_tools_lab.config import BoardConfig
from restore_tools_lab.serial_utils import SerialError
from restore_tools_lab.verify_utils import (
    VerifyError,
    VerifyResult,
    verify_boot,
    verify_boot_from_lines,
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


# --------------------------------------------------------------------------- #
# verify_boot_from_lines
# --------------------------------------------------------------------------- #


def test_verify_from_lines_marker_present():
    cfg = make_cfg()
    lines = ["Starting board", "BOOT_OK", "Running application"]
    result = verify_boot_from_lines(cfg, lines)
    assert result.passed is True
    assert result.status == "PASS"


def test_verify_from_lines_marker_absent():
    cfg = make_cfg()
    lines = ["Starting board", "ERROR: fault", "halted"]
    result = verify_boot_from_lines(cfg, lines)
    assert result.passed is False
    assert result.status == "FAIL"


def test_verify_from_lines_empty():
    cfg = make_cfg()
    result = verify_boot_from_lines(cfg, [])
    assert result.passed is False


def test_verify_from_lines_marker_substring():
    """Marker should match as a substring inside a line."""
    cfg = make_cfg()
    lines = ["[INFO] BOOT_OK received — continuing"]
    result = verify_boot_from_lines(cfg, lines)
    assert result.passed is True


def test_verify_from_lines_stores_lines():
    cfg = make_cfg()
    lines = ["a", "BOOT_OK", "b"]
    result = verify_boot_from_lines(cfg, lines)
    assert result.lines_received == lines


def test_verify_from_lines_board_name():
    cfg = make_cfg(board_name="bl475e_iot01a")
    result = verify_boot_from_lines(cfg, ["BOOT_OK"])
    assert result.board_name == "bl475e_iot01a"


# --------------------------------------------------------------------------- #
# verify_boot (live port — mocked)
# --------------------------------------------------------------------------- #


@patch(
    "restore_tools_lab.verify_utils.wait_for_marker",
    return_value=(True, ["init", "BOOT_OK"]),
)
def test_verify_boot_passes(mock_wait):
    cfg = make_cfg()
    result = verify_boot(cfg)
    assert result.passed is True


@patch(
    "restore_tools_lab.verify_utils.wait_for_marker",
    return_value=(False, ["init", "error"]),
)
def test_verify_boot_fails(mock_wait):
    cfg = make_cfg()
    result = verify_boot(cfg)
    assert result.passed is False


@patch(
    "restore_tools_lab.verify_utils.wait_for_marker",
    side_effect=SerialError("port not found"),
)
def test_verify_boot_serial_error_raises_verify_error(mock_wait):
    cfg = make_cfg()
    with pytest.raises(VerifyError, match="port not found"):
        verify_boot(cfg)


@patch(
    "restore_tools_lab.verify_utils.wait_for_marker",
    return_value=(True, ["BOOT_OK"]),
)
def test_verify_boot_timeout_override(mock_wait):
    cfg = make_cfg()
    result = verify_boot(cfg, timeout_sec=99)
    mock_wait.assert_called_once_with(cfg, timeout_sec=99)
    assert result.passed is True


# --------------------------------------------------------------------------- #
# VerifyResult helpers
# --------------------------------------------------------------------------- #


def test_verify_result_str_pass():
    r = VerifyResult(True, "nucleo", "BOOT_OK", ["BOOT_OK"])
    assert "PASS" in str(r)


def test_verify_result_str_fail():
    r = VerifyResult(False, "nucleo", "BOOT_OK", [])
    assert "FAIL" in str(r)


def test_verify_result_marker_in_str():
    r = VerifyResult(True, "nucleo", "BOOT_OK", [])
    assert "BOOT_OK" in str(r)


# --------------------------------------------------------------------------- #
# Both boards
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("board", ["nucleo_f411re", "bl475e_iot01a"])
def test_both_boards_pass(board: str):
    cfg = make_cfg(board_name=board)
    result = verify_boot_from_lines(cfg, ["boot start", "BOOT_OK", "running"])
    assert result.passed is True
    assert result.board_name == board


@pytest.mark.parametrize("board", ["nucleo_f411re", "bl475e_iot01a"])
def test_both_boards_fail(board: str):
    cfg = make_cfg(board_name=board)
    result = verify_boot_from_lines(cfg, ["fault at 0x080012bc", "halted"])
    assert result.passed is False
