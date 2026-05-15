# Firmware

This folder holds the lab firmware images used for flashing exercises, boot verification,
and failure injection.

## Image Types

| Folder | Purpose | Expected Outcome |
|--------|---------|-----------------|
| `blink/` | Known-good build | LED blinks; board boots cleanly |
| `boot_marker/` | Prints `BOOT_OK` over UART | `verify` command passes |
| `bad_image/` | Intentionally invalid/corrupt | Flash or boot failure; use for triage practice |

## Building Firmware

This lab does not include pre-built `.bin` files — you provide your own.
The folder structure reserves a place for each image type.

### Option 1: STM32CubeIDE

1. Open STM32CubeIDE and create a new project for your target board.
2. Select the correct MCU/board (NUCLEO-F411RE or B-L475E-IOT01A).
3. For `blink/`: configure a GPIO output on the LED pin and toggle it in a loop.
4. For `boot_marker/`: add a `HAL_UART_Transmit` call that sends `BOOT_OK\r\n`
   at startup (before the main loop).
5. Build the project and copy the `.bin` from the `build/` folder into the
   appropriate subfolder here.

### Option 2: STM32CubeMX + Makefile

Generate code with STM32CubeMX, then build with `make` in the generated folder.
Copy the resulting `.bin` here.

### Option 3: Use an Existing Demo Binary

STMicroelectronics provides demo applications for evaluation boards on their
website. You can use any demo `.bin` as the `blink/` image — just note that
it will not print `BOOT_OK` unless you modify it.

## Placement

```
firmware/
├── blink/
│   ├── README.md
│   └── blink.bin          ← place your compiled binary here
├── boot_marker/
│   ├── README.md
│   └── boot_marker.bin    ← place your compiled binary here
└── bad_image/
    ├── README.md
    └── bad_image.bin      ← place your intentionally broken binary here
```

## Creating a bad_image

The easiest bad image is a file filled with zeroes or random bytes:

```bash
# All-zeroes file (causes boot failure on STM32 — invalid vector table)
dd if=/dev/zero of=firmware/bad_image/bad_image.bin bs=1024 count=4

# Random bytes (same effect)
dd if=/dev/urandom of=firmware/bad_image/bad_image.bin bs=1024 count=4
```

STM32 checks the initial stack pointer and reset handler address at boot.
An invalid vector table causes the MCU to fault immediately, producing no
serial output — which is exactly the condition the triage playbook covers.
