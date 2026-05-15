# Board Notes

Reference notes for the two boards used in this lab.

---

## NUCLEO-F411RE

| Field | Value |
|-------|-------|
| MCU | STM32F411RET6 (Cortex-M4, 100 MHz, 512 KB flash, 128 KB RAM) |
| Config file | `configs/nucleo_f411re.yaml` |
| Flash address | `0x08000000` |
| Baud rate | 115200 |
| Debug interface | On-board ST-LINK/V2-1 (SWD) |
| Virtual COM port | Exposed over same USB connector as ST-LINK |
| Morpho headers | 2× 38-pin Morpho (CN7, CN10) |
| Arduino headers | Yes (CN5, CN6, CN8, CN9) |

### Board-Specific Notes

- The ST-LINK firmware can be updated via the STM32CubeProgrammer or the
  STSW-LINK007 utility. Keep it up to date for reliable SWD connectivity.
- The on-board LED (LD2, green) is connected to PA5 and is used by the blink
  firmware as a visual indicator.
- BOOT0 is pulled low by default (normal flash boot). Do not change unless
  deliberately entering DFU mode.
- The NUCLEO exposes SB13/SB14 solder bridges that control UART2 routing to
  the ST-LINK virtual COM port — these are closed by default.

### Typical Serial Port Paths

| OS | Path |
|----|------|
| macOS | `/dev/tty.usbmodem14101` (number varies) |
| Linux | `/dev/ttyACM0` |
| Windows | `COM3` (check Device Manager) |

---

## B-L475E-IOT01A

| Field | Value |
|-------|-------|
| MCU | STM32L475VGT6 (Cortex-M4, 80 MHz, 1 MB flash, 128 KB RAM) |
| Config file | `configs/bl475e_iot01a.yaml` |
| Flash address | `0x08000000` |
| Baud rate | 115200 |
| Debug interface | On-board ST-LINK/V2-1 (SWD) |
| Virtual COM port | Exposed over ST-LINK USB connector (CN7) |
| IoT peripherals | Wi-Fi (ISM43362-M3G-L44), BLE (SPBTLE-RF), sensors (HTS221, LPS22HB, LSM303AGR, LSM6DSL, MP34DT01, VL53L0X) |

### Board-Specific Notes

- The L475 is an ultra-low-power MCU. Some power configurations may affect
  serial output timing — if the boot marker is intermittent, check that the
  MCU is not entering low-power modes before the UART TX completes.
- Wi-Fi module initialization can add 2–4 seconds to the boot sequence. If
  your firmware initializes the ISM43362, increase `timeout_sec` to at least
  30 in the config.
- The BLE module uses a separate SPI interface and does not affect UART output.
- Flash memory starts at `0x08000000` (same as all STM32 devices). No changes
  needed to the flash address vs. the NUCLEO config.
- Two USB connectors: CN7 (ST-LINK, use this one) and CN1 (USB OTG, not used
  in this lab).

### Typical Serial Port Paths

| OS | Path |
|----|------|
| macOS | `/dev/tty.usbmodem14201` (number varies) |
| Linux | `/dev/ttyACM0` or `/dev/ttyACM1` if NUCLEO also connected |
| Windows | `COM4` (check Device Manager) |

---

## Common to Both Boards

- Both boards use STM32CubeProgrammer with the SWD (`STLINK`) interface.
- Both expose `0x08000000` as the main flash start address.
- Both provide a virtual COM port over the on-board ST-LINK USB connection.
- Both support the `--reset` flag in STM32CubeProgrammer to reboot after flash.
- BOOT0 pin is pulled low on both boards (normal flash boot mode).

## USB Cable Requirements

Use a USB cable that supports data (not just charging). Many micro-USB cables
are charge-only and will not enumerate the ST-LINK or virtual COM port.

Test by running `lsusb` (Linux), `system_profiler SPUSBDataType` (macOS),
or checking Device Manager (Windows) — you should see an STMicroelectronics
device listed.
