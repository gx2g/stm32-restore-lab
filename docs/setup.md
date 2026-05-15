# Setup

## Prerequisites

- Python 3.10+
- STM32CubeProgrammer installed and available on PATH as `STM32_Programmer_CLI`
- `pyserial`
- `pyyaml`
- `pytest` for tests

## Create Environment

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e .[dev]
```

## Verify Tool Access

```bash
STM32_Programmer_CLI --help
python -c "import serial, yaml"
restore-tools-lab --help
pytest
```

## Board Preparation

### NUCLEO-F411RE

1. Connect the board via the on-board ST-LINK USB connector (not the user USB port).
2. Confirm the ST-LINK interface is detected — the green LED on the board should blink.
3. Confirm the virtual COM port appears:
   - Linux/macOS: `ls /dev/tty.*` or `ls /dev/ttyACM*`
   - Windows: check Device Manager → Ports
4. Edit `configs/nucleo_f411re.yaml` → set `serial_port` to the detected device path.

### B-L475E-IOT01A

1. Connect the board via the ST-LINK USB connector (CN7).
2. Same ST-LINK detection steps as above.
3. Edit `configs/bl475e_iot01a.yaml` → set `serial_port` to the detected device path.

### Serial Port Identification

| OS | Typical ST-LINK virtual COM port |
|----|-----------------------------------|
| macOS | `/dev/tty.usbmodem*` |
| Linux | `/dev/ttyACM0` or `/dev/ttyUSB0` |
| Windows | `COM3`, `COM4`, etc. |

## Basic Run Sequence

### NUCLEO-F411RE

```bash
restore-tools-lab flash \
  --config configs/nucleo_f411re.yaml \
  --image firmware/blink/blink.bin

restore-tools-lab verify --config configs/nucleo_f411re.yaml

restore-tools-lab cycle \
  --config configs/nucleo_f411re.yaml \
  --image firmware/blink/blink.bin
```

### B-L475E-IOT01A

```bash
restore-tools-lab flash \
  --config configs/bl475e_iot01a.yaml \
  --image firmware/blink/blink.bin

restore-tools-lab verify --config configs/bl475e_iot01a.yaml

restore-tools-lab cycle \
  --config configs/bl475e_iot01a.yaml \
  --image firmware/blink/blink.bin
```

## Troubleshooting Setup

| Symptom | Check |
|---------|-------|
| `STM32_Programmer_CLI: command not found` | STM32CubeProgrammer not installed or not on PATH |
| `ModuleNotFoundError: serial` | Run `pip install pyserial` |
| Port not found | Board not connected; wrong cable (use data cable, not charge-only) |
| Permission denied on serial port (Linux) | Add user to `dialout` group: `sudo usermod -aG dialout $USER` |
