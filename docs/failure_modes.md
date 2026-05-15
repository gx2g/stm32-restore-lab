# Failure Modes

This document catalogues the known failure modes for the restore-tools-lab workflows.
For each mode: symptoms, likely causes, and suggested fixes.

---

## Wrong Serial Port

**Symptoms**
- Tool times out waiting for the boot marker.
- No boot text appears in the log.
- `capture_serial` returns an empty `CaptureResult`.

**Likely Causes**
- Wrong COM device selected in the board config.
- Board not connected.
- Charge-only USB cable used instead of a data cable.
- Multiple virtual COM ports present; wrong one selected.

**Fix**
- Run `ls /dev/tty.*` (macOS) or `ls /dev/ttyACM*` (Linux) to list available ports.
- Connect the board and diff the port list before/after to identify the new device.
- Update `serial_port` in the YAML config.

---

## Wrong Baud Rate

**Symptoms**
- Garbled output (random characters, question marks).
- Boot marker string never appears even though the board is transmitting.

**Likely Causes**
- Serial settings mismatch between firmware and host config.

**Fix**
- Confirm the baud rate used in the firmware (usually 115200 for ST eval boards).
- Update `baud_rate` in the YAML config.

---

## Flash Failure

**Symptoms**
- Flash command exits with a non-zero return code.
- `FlashResult.success` is False.
- Board does not reboot cleanly after flashing.
- STM32CubeProgrammer reports connection error.

**Likely Causes**
- `STM32_Programmer_CLI` not installed or not on PATH.
- SWD cable not connected or ST-LINK not detected.
- Board is not powered.
- Image path invalid or file does not exist.
- BOOT0 pin state preventing programming mode entry.

**Fix**
- Verify: `STM32_Programmer_CLI --help` runs without error.
- Check: ST-LINK LED is solid (not blinking fast = fault).
- Check: image file exists: `ls -lh firmware/blink/blink.bin`.
- Try opening STM32CubeProgrammer GUI to confirm SWD connectivity before using CLI.

---

## Boot Failure (No Marker)

**Symptoms**
- Flash step succeeds (rc=0, verify pass in CubeProgrammer).
- Serial output is received but never contains the boot marker.
- `VerifyResult.passed` is False.

**Likely Causes**
- Bad or incorrect firmware image.
- Wrong `boot_marker` string in the config (case sensitive).
- Application crashes before reaching the boot print.
- Reset timing: serial capture starts before the board has reset and begun transmitting.

**Fix**
- Check `boot_marker` in the YAML matches exactly what the firmware prints (case, spaces).
- Flash the `boot_marker` reference image and re-test.
- Add a short delay before calling `verify` to allow for board reset enumeration.
- Check for application HardFault by reading raw serial output with a terminal (e.g. `screen`, `minicom`).

---

## Timing / Race Condition

**Symptoms**
- Intermittent pass/fail across repeated runs.
- Works after a retry but fails on the first attempt.
- Occasional partial boot marker (truncated string).

**Likely Causes**
- USB re-enumeration delay after reset.
- Serial capture starts too early, before the board has reset.
- Reset timing race between STM32CubeProgrammer releasing the chip and the serial read opening.

**Fix**
- Increase `timeout_sec` in the board config to give the board more time.
- Add a deliberate sleep between `flash` and `verify` steps in the cycle.
- Use the `--duration` flag on `log` to extend the capture window.

---

## STM32CubeProgrammer Not on PATH

**Symptoms**
- `FlashError: Programmer CLI not found on PATH: 'STM32_Programmer_CLI'`.

**Fix (macOS)**
```bash
export PATH="/Applications/STMicroelectronics/STM32Cube/STM32CubeProgrammer/STM32CubeProgrammer.app/Contents/MacOs/bin:$PATH"
```

**Fix (Linux)**
```bash
export PATH="$HOME/STMicroelectronics/STM32Cube/STM32CubeProgrammer/bin:$PATH"
```

**Fix (Windows)**
Add the CubeProgrammer `bin` folder to the system PATH via System Properties → Environment Variables.

---

## Python Import Error

**Symptoms**
- `ModuleNotFoundError: No module named 'serial'`
- `ModuleNotFoundError: No module named 'yaml'`

**Fix**
```bash
pip install pyserial pyyaml
# or
pip install -e .[dev]
```

---

## Config Validation Error

**Symptoms**
- `ConfigError: Board config is missing required field(s): …`
- `ConfigError: flash_address should be a hex string …`

**Fix**
- Check the YAML file for typos or missing keys.
- Compare against the reference configs in `configs/`.
- Ensure `flash_address` starts with `0x`.
