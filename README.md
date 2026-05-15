# restore-tools-lab

A small embedded tooling lab for practicing restore-style workflows on STM32 boards.

This project simulates the kind of host-side engineering work done in restore tooling roles:

- Python automation.
- Device flashing and reset.
- Serial logging and boot verification.
- Failure injection and triage.
- Reusable documentation and support notes.

## Goals

Build confidence in the workflows that matter for restore infrastructure:

- Flash a known-good image.
- Capture serial output.
- Verify a boot marker.
- Record failures in a repeatable way.
- Document how to troubleshoot common issues.

## Supported Boards

| Board | Config File |
|-------|-------------|
| NUCLEO-F411RE | `configs/nucleo_f411re.yaml` |
| B-L475E-IOT01A | `configs/bl475e_iot01a.yaml` |

Both boards expose on-board ST-LINK debug/programming support and virtual COM port workflows,
which are useful for flash, reset, and serial verification exercises.

## Repository Layout

```text
restore-tools-lab/
├── README.md
├── LICENSE
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── configs/
│   ├── nucleo_f411re.yaml
│   └── bl475e_iot01a.yaml
├── docs/
│   ├── setup.md
│   ├── triage_playbook.md
│   ├── failure_modes.md
│   └── board_notes.md
├── firmware/
│   ├── README.md
│   ├── blink/
│   │   └── README.md
│   ├── boot_marker/
│   │   └── README.md
│   └── bad_image/
│       └── README.md
├── logs/
│   ├── raw/
│   └── reports/
├── output/
│   ├── csv/
│   └── charts/
├── src/
│   └── restore_tools_lab/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── flash_utils.py
│       ├── serial_utils.py
│       ├── verify_utils.py
│       └── report_utils.py
└── tests/
    ├── test_config.py
    ├── test_flash_utils.py
    ├── test_serial_utils.py
    └── test_verify_utils.py
```

## Prerequisites

- Python 3.10 or newer.
- STM32CubeProgrammer installed and available on PATH as `STM32_Programmer_CLI`.
- `pyserial`.
- `pyyaml`.
- `pytest` for local tests.

## Install

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e .[dev]
```

## Verify Setup

```bash
STM32_Programmer_CLI --help
restore-tools-lab --help
python -c "import serial, yaml"
pytest
```

## Typical Workflow

1. Choose a board config.
2. Flash a known-good image.
3. Capture serial output.
4. Verify the expected boot marker.
5. Save logs and result records.
6. Update triage docs if anything fails.

## Command-Line Usage

### Flash a board

```bash
restore-tools-lab flash \
  --config configs/nucleo_f411re.yaml \
  --image firmware/blink/blink.bin
```

### Capture serial logs

```bash
restore-tools-lab log \
  --config configs/nucleo_f411re.yaml \
  --duration 30 \
  --output logs/raw/nucleo.log
```

### Verify boot output

```bash
restore-tools-lab verify --config configs/nucleo_f411re.yaml
```

### Run a full flash-verify cycle

```bash
restore-tools-lab cycle \
  --config configs/bl475e_iot01a.yaml \
  --image firmware/blink/blink.bin
```

The `cycle` command flashes the image, waits for the boot marker, and writes a result
record into `output/csv/`.

### Inject a failure for practice

```bash
restore-tools-lab cycle \
  --config configs/nucleo_f411re.yaml \
  --image firmware/bad_image/bad_image.bin
```

## Board Configs

Each YAML config carries the serial port, baud rate, flashing interface, boot marker, and
timeout settings. Edit the `serial_port` field to match your host:

| Field | Purpose |
|---|---|
| `board_name` | Identifier used in log filenames and reports |
| `serial_port` | Host serial device path (e.g. `/dev/tty.usbserial-…` or `COM3`) |
| `baud_rate` | Serial baud rate (typically 115200) |
| `flash_tool` | Friendly name of the flash tool |
| `swd_interface` | SWD probe type (`STLINK`) |
| `boot_marker` | String the firmware prints when boot succeeds |
| `flash_address` | Start address for flashing (`0x08000000` for STM32) |
| `timeout_sec` | Seconds to wait for the boot marker |
| `programmer_cli` | Executable name on PATH |

## Firmware Images

| Folder | Purpose |
|---|---|
| `blink/` | Known-good build — use for baseline flash and cycle tests |
| `boot_marker/` | Prints `BOOT_OK` over UART — use for verify tests |
| `bad_image/` | Intentionally invalid — use for failure injection practice |

Place compiled `.bin` files inside the relevant folder before running commands.

## Failure Injection Ideas

Try deliberately causing:

- Wrong serial port.
- Wrong baud rate.
- Bad firmware image.
- Cable disconnect mid-flash.
- Reset timing race.
- Flash timeout.

For each failure, capture what happened, what the serial log showed, what the flash tool
returned, and what fixed it. Document the result in `docs/triage_playbook.md`.

## Triage Rule

If a run fails, determine whether the issue is:

- Host-side tooling.
- Serial connection.
- Flashing step.
- Reset behavior.
- Device firmware.

Document the answer in `docs/triage_playbook.md`.

## Tests

```bash
pytest
pytest -v                    # verbose
pytest tests/test_config.py  # single module
```

## What This Project Teaches

- Python scripting for embedded tooling.
- Host/device integration patterns.
- Serial and flash debugging.
- Repeatable automation design.
- Clear technical documentation.

## Next Steps

- Add result charts from `output/csv/`.
- Add more failure modes.
- Add retries and backoff to the cycle command.
- Add a small log parser.
- Add a support-style triage FAQ.
