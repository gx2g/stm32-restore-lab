# blink

Known-good firmware image. The board LED blinks at a fixed interval.

## What it does

- Configures a GPIO output connected to the on-board LED.
- Toggles the LED in a `while(1)` loop with a `HAL_Delay(500)` between toggles.
- Does **not** print any UART output by default (use `boot_marker` for serial verification).

## Expected Outcome

| Step | Expected |
|------|----------|
| Flash | `FlashResult.success = True`, `returncode = 0` |
| LED | Blinks at ~1 Hz (on 500ms, off 500ms) |
| Verify | Will FAIL (no `BOOT_OK` output) — use `boot_marker` image for verify tests |

## Boards

Works on both NUCLEO-F411RE (LED = PA5) and B-L475E-IOT01A (LED = PA5 / PB14).

## Placement

Place the compiled binary here as `blink.bin`.

```bash
restore-tools-lab flash --config configs/nucleo_f411re.yaml --image firmware/blink/blink.bin
```
