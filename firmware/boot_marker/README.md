# boot_marker

Firmware that prints a known boot marker string over UART at startup.
Use this image for `verify` and `cycle` tests.

## What it does

At startup, before entering the main loop, the firmware transmits:

```
BOOT_OK\r\n
```

over UART2 at 115200 baud (the ST-LINK virtual COM port on both NUCLEO and B-L475E).

The marker string must match `boot_marker` in the board YAML config exactly.

## Expected Outcome

| Step | Expected |
|------|----------|
| Flash | `FlashResult.success = True`, `returncode = 0` |
| Serial output | Contains `BOOT_OK` within `timeout_sec` seconds |
| Verify | `VerifyResult.passed = True` |
| Cycle | `CycleRecord.overall_pass = True` |

## Minimal Firmware Snippet

```c
/* In main.c, after MX_USART2_UART_Init() */
const char *marker = "BOOT_OK\r\n";
HAL_UART_Transmit(&huart2, (uint8_t *)marker, strlen(marker), HAL_MAX_DELAY);

/* Then enter the main loop */
while (1) {
    HAL_Delay(1000);
}
```

## Placement

Place the compiled binary here as `boot_marker.bin`.

```bash
restore-tools-lab cycle \
  --config configs/nucleo_f411re.yaml \
  --image firmware/boot_marker/boot_marker.bin
```
