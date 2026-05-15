# Triage Playbook

## Goal

Use the smallest amount of evidence to determine where the failure lives:
host tool, serial link, flash step, reset path, or device firmware.

---

## Triage Order

Work top-down. Stop when you find the failure layer.

1. **Confirm the board is connected.**
   - Is the ST-LINK LED on?
   - Does `ls /dev/tty*` show the virtual COM port?

2. **Confirm the serial port is correct.**
   - Open a terminal emulator (`screen /dev/ttyACM0 115200`) and check for output.
   - If no output, check the cable, baud rate, and port path.

3. **Confirm the flash step succeeds.**
   - Run `restore-tools-lab flash --config … --image …`.
   - Check `FlashResult.success` and `returncode`.
   - Non-zero rc → flash layer failure. See `docs/failure_modes.md#flash-failure`.

4. **Confirm the board resets after flashing.**
   - The LED pattern should change after flashing (blink firmware blinks).
   - If the board appears unresponsive, try a manual reset (RESET button).

5. **Confirm the boot marker appears.**
   - Run `restore-tools-lab verify --config …`.
   - If the marker does not appear, check `boot_marker` in the YAML and compare
     to raw serial output.

6. **Save logs and results.**
   - Check `output/csv/<board>_results.csv` for the result record.
   - Check `output/<board>_<timestamp>.txt` for the text triage report.

---

## Questions to Answer for Every Failure

| Question | Where to look |
|----------|---------------|
| Did flashing succeed? | `FlashResult.success`, `returncode` |
| Did the board reset? | LED pattern, timing of serial output |
| Did serial output appear? | `CaptureResult.lines`, raw log |
| Was the boot marker seen? | `VerifyResult.passed` |
| Is the failure reproducible? | Run the cycle 3× and compare `output/csv/` |

---

## Failure Layer Decision Tree

```
Cycle FAIL
│
├── Flash returned non-zero?
│   YES → Flash layer.  Check: CLI on PATH, SWD connected, image valid.
│
├── Flash OK but no serial output at all?
│   YES → Serial layer.  Check: port path, baud rate, cable, permissions.
│
├── Serial output present but marker not found?
│   YES → Firmware/boot layer.  Check: boot_marker string, firmware image, reset timing.
│
└── All steps pass but cycle still fails?
    YES → Report layer or config mismatch.  Check: output paths, YAML consistency.
```

---

## Board-Specific Notes

### NUCLEO-F411RE

- The on-board ST-LINK also provides the virtual COM port (single USB cable).
- After `--reset` in STM32CubeProgrammer, the board may take ~500ms to re-enumerate.
- If the COM port disappears mid-session, unplug/replug and re-check the port path.

### B-L475E-IOT01A

- Same ST-LINK architecture as NUCLEO but also has Bluetooth and Wi-Fi modules.
- Those radios can produce extra UART traffic — the `boot_marker` read will still
  work because `wait_for_marker` stops as soon as the marker is found.
- If using the ISM43362 Wi-Fi module in firmware, expect a longer boot sequence
  — increase `timeout_sec` to 30–45 if the marker appears late.

---

## Triage Log Template

Copy this into `logs/reports/` for each investigated failure:

```
Date       :
Board      :
Image      :
Symptom    :
Flash rc   :
Serial out : (paste first 10 lines)
Marker seen: yes / no
Root cause :
Fix applied:
Verified   : yes / no
```

---

## Reference Commands

```bash
# Quick board-to-board comparison
restore-tools-lab cycle --config configs/nucleo_f411re.yaml --image firmware/blink/blink.bin
restore-tools-lab cycle --config configs/bl475e_iot01a.yaml --image firmware/blink/blink.bin

# Capture raw serial to inspect manually
restore-tools-lab log --config configs/nucleo_f411re.yaml --duration 30 --output logs/raw/nucleo_raw.log

# Inject a known failure
restore-tools-lab cycle --config configs/nucleo_f411re.yaml --image firmware/bad_image/bad_image.bin
```
