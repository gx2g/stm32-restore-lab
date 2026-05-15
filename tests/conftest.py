"""
Shared pytest fixtures for restore-tools-lab.

Fixtures here are available to all test modules without explicit import.
Both board configurations (NUCLEO-F411RE and B-L475E-IOT01A) are provided
as fixtures so tests can exercise board-specific behaviour.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from restore_tools_lab.config import BoardConfig

# --------------------------------------------------------------------------- #
# Base config data
# --------------------------------------------------------------------------- #

_NUCLEO_DATA = {
    "board_name": "nucleo_f411re",
    "serial_port": "/dev/ttyACM0",
    "baud_rate": 115200,
    "flash_tool": "STM32CubeProgrammer",
    "swd_interface": "STLINK",
    "boot_marker": "BOOT_OK",
    "flash_address": "0x08000000",
    "timeout_sec": 20,
    "programmer_cli": "STM32_Programmer_CLI",
}

_BL475_DATA = {
    "board_name": "bl475e_iot01a",
    "serial_port": "/dev/ttyACM1",
    "baud_rate": 115200,
    "flash_tool": "STM32CubeProgrammer",
    "swd_interface": "STLINK",
    "boot_marker": "BOOT_OK",
    "flash_address": "0x08000000",
    "timeout_sec": 20,
    "programmer_cli": "STM32_Programmer_CLI",
}


# --------------------------------------------------------------------------- #
# Board config fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture()
def nucleo_cfg() -> BoardConfig:
    """Validated BoardConfig for the NUCLEO-F411RE."""
    return BoardConfig.from_dict(_NUCLEO_DATA)


@pytest.fixture()
def bl475_cfg() -> BoardConfig:
    """Validated BoardConfig for the B-L475E-IOT01A."""
    return BoardConfig.from_dict(_BL475_DATA)


@pytest.fixture(params=["nucleo_f411re", "bl475e_iot01a"])
def any_board_cfg(request: pytest.FixtureRequest) -> BoardConfig:
    """
    Parametrised fixture that yields one BoardConfig per board.

    Tests using this fixture run twice — once per board — so coverage is
    guaranteed for both targets without duplicating test logic.

    Usage::

        def test_something(any_board_cfg):
            result = verify_boot_from_lines(any_board_cfg, ["BOOT_OK"])
            assert result.passed
    """
    data = _NUCLEO_DATA if request.param == "nucleo_f411re" else _BL475_DATA
    return BoardConfig.from_dict(data)


# --------------------------------------------------------------------------- #
# Filesystem fixtures
# --------------------------------------------------------------------------- #


@pytest.fixture()
def fake_image(tmp_path: Path) -> Path:
    """A dummy 256-byte binary file standing in for a real .bin image."""
    p = tmp_path / "blink.bin"
    p.write_bytes(b"\xDE\xAD\xBE\xEF" * 64)
    return p


@pytest.fixture()
def bad_image(tmp_path: Path) -> Path:
    """A zero-filled file representing an invalid firmware image."""
    p = tmp_path / "bad_image.bin"
    p.write_bytes(b"\x00" * 256)
    return p


@pytest.fixture()
def nucleo_yaml(tmp_path: Path) -> Path:
    """Write a NUCLEO YAML config to a temp file and return the path."""
    import yaml

    p = tmp_path / "nucleo_f411re.yaml"
    p.write_text(yaml.dump(_NUCLEO_DATA), encoding="utf-8")
    return p


@pytest.fixture()
def bl475_yaml(tmp_path: Path) -> Path:
    """Write a BL475 YAML config to a temp file and return the path."""
    import yaml

    p = tmp_path / "bl475e_iot01a.yaml"
    p.write_text(yaml.dump(_BL475_DATA), encoding="utf-8")
    return p
