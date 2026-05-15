"""Tests for restore_tools_lab.config."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml

from restore_tools_lab.config import BoardConfig, ConfigError

# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

VALID_DATA = {
    "board_name": "nucleo_f411re",
    "serial_port": "/dev/tty.usbserial-NUCLEO",
    "baud_rate": 115200,
    "flash_tool": "STM32CubeProgrammer",
    "swd_interface": "STLINK",
    "boot_marker": "BOOT_OK",
    "flash_address": "0x08000000",
    "timeout_sec": 20,
    "programmer_cli": "STM32_Programmer_CLI",
}


def make_yaml_file(tmp_path: Path, data: dict) -> Path:
    """Write a YAML file from *data* and return its path."""
    p = tmp_path / "board.yaml"
    p.write_text(yaml.dump(data), encoding="utf-8")
    return p


# --------------------------------------------------------------------------- #
# from_dict
# --------------------------------------------------------------------------- #


def test_from_dict_valid():
    cfg = BoardConfig.from_dict(VALID_DATA)
    assert cfg.board_name == "nucleo_f411re"
    assert cfg.baud_rate == 115200
    assert cfg.boot_marker == "BOOT_OK"


def test_from_dict_extra_fields_stored():
    data = {**VALID_DATA, "custom_field": "hello"}
    cfg = BoardConfig.from_dict(data)
    assert cfg.extras["custom_field"] == "hello"


@pytest.mark.parametrize("missing_field", list(VALID_DATA.keys()))
def test_from_dict_missing_field_raises(missing_field: str):
    data = {k: v for k, v in VALID_DATA.items() if k != missing_field}
    with pytest.raises(ConfigError, match="missing required field"):
        BoardConfig.from_dict(data)


def test_from_dict_negative_baud_raises():
    data = {**VALID_DATA, "baud_rate": -1}
    with pytest.raises(ConfigError, match="baud_rate"):
        BoardConfig.from_dict(data)


def test_from_dict_zero_timeout_raises():
    data = {**VALID_DATA, "timeout_sec": 0}
    with pytest.raises(ConfigError, match="timeout_sec"):
        BoardConfig.from_dict(data)


def test_from_dict_empty_marker_raises():
    data = {**VALID_DATA, "boot_marker": "   "}
    with pytest.raises(ConfigError, match="boot_marker"):
        BoardConfig.from_dict(data)


def test_from_dict_bad_flash_address_raises():
    data = {**VALID_DATA, "flash_address": "8000000"}  # missing 0x prefix
    with pytest.raises(ConfigError, match="flash_address"):
        BoardConfig.from_dict(data)


# --------------------------------------------------------------------------- #
# from_file
# --------------------------------------------------------------------------- #


def test_from_file_valid(tmp_path: Path):
    p = make_yaml_file(tmp_path, VALID_DATA)
    cfg = BoardConfig.from_file(p)
    assert cfg.board_name == VALID_DATA["board_name"]
    assert cfg.flash_address == "0x08000000"


def test_from_file_not_found_raises(tmp_path: Path):
    with pytest.raises(ConfigError, match="not found"):
        BoardConfig.from_file(tmp_path / "nonexistent.yaml")


def test_from_file_bad_yaml_raises(tmp_path: Path):
    p = tmp_path / "bad.yaml"
    p.write_text("key: [unclosed bracket", encoding="utf-8")
    with pytest.raises(ConfigError, match="YAML"):
        BoardConfig.from_file(p)


def test_from_file_non_mapping_raises(tmp_path: Path):
    p = tmp_path / "list.yaml"
    p.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="mapping"):
        BoardConfig.from_file(p)


# --------------------------------------------------------------------------- #
# BoardConfig helpers
# --------------------------------------------------------------------------- #


def test_as_dict_round_trip():
    cfg = BoardConfig.from_dict(VALID_DATA)
    d = cfg.as_dict()
    for key, val in VALID_DATA.items():
        assert d[key] == val


def test_as_dict_includes_extras():
    data = {**VALID_DATA, "some_extra": 42}
    cfg = BoardConfig.from_dict(data)
    assert cfg.as_dict()["some_extra"] == 42


# --------------------------------------------------------------------------- #
# Both boards (integration-style config tests)
# --------------------------------------------------------------------------- #


BOARDS = [
    "configs/nucleo_f411re.yaml",
    "configs/bl475e_iot01a.yaml",
]


@pytest.mark.parametrize("config_file", BOARDS)
def test_board_configs_load(config_file: str):
    """Ensure the shipped board configs are valid."""
    path = Path(config_file)
    if not path.exists():
        pytest.skip(f"Config not found at {config_file} (run from project root).")
    cfg = BoardConfig.from_file(path)
    assert cfg.baud_rate > 0
    assert cfg.boot_marker
