"""Tests for restore_tools_lab.cli."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from restore_tools_lab.cli import main
from restore_tools_lab.flash_utils import FlashResult
from restore_tools_lab.verify_utils import VerifyResult


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _flash_ok(cmd=None) -> FlashResult:
    return FlashResult(True, 0, "ok", "", cmd or ["STM32_Programmer_CLI"])


def _flash_fail(cmd=None) -> FlashResult:
    return FlashResult(False, 1, "", "SWD error", cmd or ["STM32_Programmer_CLI"])


def _verify_pass(cfg=None) -> VerifyResult:
    cfg_name = cfg.board_name if cfg else "nucleo_f411re"
    return VerifyResult(True, cfg_name, "BOOT_OK", ["BOOT_OK"])


def _verify_fail(cfg=None) -> VerifyResult:
    cfg_name = cfg.board_name if cfg else "nucleo_f411re"
    return VerifyResult(False, cfg_name, "BOOT_OK", ["no marker here"])


# --------------------------------------------------------------------------- #
# --version and --help
# --------------------------------------------------------------------------- #


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "restore-tools-lab" in out


def test_help_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help"])
    assert exc.value.code == 0


# --------------------------------------------------------------------------- #
# Config errors
# --------------------------------------------------------------------------- #


def test_missing_config_returns_2(tmp_path: Path):
    rc = main(["flash", "--config", str(tmp_path / "ghost.yaml"), "--image", "x.bin"])
    assert rc == 2


def test_bad_yaml_returns_2(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("not: [valid: yaml", encoding="utf-8")
    rc = main(["flash", "--config", str(bad), "--image", "x.bin"])
    assert rc == 2


# --------------------------------------------------------------------------- #
# flash sub-command
# --------------------------------------------------------------------------- #


@patch("restore_tools_lab.cli.flash_image", return_value=_flash_ok())
def test_flash_success_returns_0(mock_flash, nucleo_yaml, fake_image):
    rc = main(["flash", "--config", str(nucleo_yaml), "--image", str(fake_image)])
    assert rc == 0


@patch("restore_tools_lab.cli.flash_image", return_value=_flash_fail())
def test_flash_failure_returns_1(mock_flash, nucleo_yaml, fake_image):
    rc = main(["flash", "--config", str(nucleo_yaml), "--image", str(fake_image)])
    assert rc == 1


@patch("restore_tools_lab.cli.flash_image", return_value=_flash_ok())
def test_flash_dry_run(mock_flash, nucleo_yaml, fake_image):
    main(["flash", "--config", str(nucleo_yaml), "--image", str(fake_image), "--dry-run"])
    _, kwargs = mock_flash.call_args
    assert kwargs.get("dry_run") is True


# --------------------------------------------------------------------------- #
# log sub-command
# --------------------------------------------------------------------------- #


@patch(
    "restore_tools_lab.cli.capture_serial",
    return_value=MagicMock(lines=["a", "b"], __len__=lambda s: 2),
)
def test_log_success_returns_0(mock_cap, nucleo_yaml):
    rc = main(["log", "--config", str(nucleo_yaml), "--duration", "1"])
    assert rc == 0


@patch("restore_tools_lab.cli.capture_serial", side_effect=Exception("port err"))
def test_log_serial_error_returns_1(mock_cap, nucleo_yaml):
    rc = main(["log", "--config", str(nucleo_yaml)])
    assert rc == 1


# --------------------------------------------------------------------------- #
# verify sub-command
# --------------------------------------------------------------------------- #


@patch("restore_tools_lab.cli.verify_boot", return_value=_verify_pass())
def test_verify_pass_returns_0(mock_verify, nucleo_yaml):
    rc = main(["verify", "--config", str(nucleo_yaml)])
    assert rc == 0


@patch("restore_tools_lab.cli.verify_boot", return_value=_verify_fail())
def test_verify_fail_returns_1(mock_verify, nucleo_yaml):
    rc = main(["verify", "--config", str(nucleo_yaml)])
    assert rc == 1


# --------------------------------------------------------------------------- #
# cycle sub-command
# --------------------------------------------------------------------------- #


@patch("restore_tools_lab.cli.verify_boot", return_value=_verify_pass())
@patch("restore_tools_lab.cli.flash_image", return_value=_flash_ok())
def test_cycle_pass_returns_0(mock_flash, mock_verify, nucleo_yaml, fake_image, tmp_path):
    rc = main([
        "cycle",
        "--config", str(nucleo_yaml),
        "--image", str(fake_image),
        "--output-dir", str(tmp_path),
    ])
    assert rc == 0


@patch("restore_tools_lab.cli.verify_boot", return_value=_verify_fail())
@patch("restore_tools_lab.cli.flash_image", return_value=_flash_ok())
def test_cycle_verify_fail_returns_1(mock_flash, mock_verify, nucleo_yaml, fake_image, tmp_path):
    rc = main([
        "cycle",
        "--config", str(nucleo_yaml),
        "--image", str(fake_image),
        "--output-dir", str(tmp_path),
    ])
    assert rc == 1


@patch("restore_tools_lab.cli.verify_boot", return_value=_verify_pass())
@patch("restore_tools_lab.cli.flash_image", return_value=_flash_fail())
def test_cycle_flash_fail_skips_verify(mock_flash, mock_verify, nucleo_yaml, fake_image, tmp_path):
    rc = main([
        "cycle",
        "--config", str(nucleo_yaml),
        "--image", str(fake_image),
        "--output-dir", str(tmp_path),
    ])
    mock_verify.assert_not_called()
    assert rc == 1


@patch("restore_tools_lab.cli.verify_boot", return_value=_verify_pass())
@patch("restore_tools_lab.cli.flash_image", return_value=_flash_ok())
def test_cycle_writes_csv(mock_flash, mock_verify, nucleo_yaml, fake_image, tmp_path):
    main([
        "cycle",
        "--config", str(nucleo_yaml),
        "--image", str(fake_image),
        "--output-dir", str(tmp_path),
    ])
    csv_files = list(tmp_path.glob("*.csv"))
    assert len(csv_files) == 1


# --------------------------------------------------------------------------- #
# Both boards via parametrised config fixtures
# --------------------------------------------------------------------------- #


@patch("restore_tools_lab.cli.verify_boot", return_value=_verify_pass())
@patch("restore_tools_lab.cli.flash_image", return_value=_flash_ok())
def test_cycle_nucleo(mock_flash, mock_verify, nucleo_yaml, fake_image, tmp_path):
    rc = main([
        "cycle", "--config", str(nucleo_yaml),
        "--image", str(fake_image), "--output-dir", str(tmp_path),
    ])
    assert rc == 0


@patch("restore_tools_lab.cli.verify_boot", return_value=_verify_pass())
@patch("restore_tools_lab.cli.flash_image", return_value=_flash_ok())
def test_cycle_bl475(mock_flash, mock_verify, bl475_yaml, fake_image, tmp_path):
    rc = main([
        "cycle", "--config", str(bl475_yaml),
        "--image", str(fake_image), "--output-dir", str(tmp_path),
    ])
    assert rc == 0
