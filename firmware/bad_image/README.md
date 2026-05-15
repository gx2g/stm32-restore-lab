# bad_image

An intentionally broken or invalid firmware image. Use this for failure injection
and triage practice.

## What it does

This is not real firmware. It contains an invalid or corrupt binary that the STM32
will either:

- Fail to flash cleanly (if the image format is severely malformed), or
- Flash successfully but immediately fault at boot (invalid vector table).

The second case — flash OK, boot FAIL — is the more interesting triage scenario:
the flash tool reports success, but the board never prints the boot marker.

## Expected Outcome

| Step | Expected |
|------|----------|
| Flash | May succeed (rc=0) or fail (non-zero rc) |
| Serial output | No `BOOT_OK` (board faults or produces garbage) |
| Verify | `VerifyResult.passed = False` |
| Cycle | `CycleRecord.overall_pass = False` |

## Creating the Bad Image

```bash
# Option 1: All-zeroes (invalid STM32 vector table)
dd if=/dev/zero of=firmware/bad_image/bad_image.bin bs=1024 count=4

# Option 2: Random bytes
dd if=/dev/urandom of=firmware/bad_image/bad_image.bin bs=1024 count=4

# Option 3: Truncate a real image (simulate incomplete flash)
cp firmware/blink/blink.bin firmware/bad_image/bad_image.bin
truncate --size=256 firmware/bad_image/bad_image.bin
```

## Triage Practice Workflow

```bash
# Inject the failure
restore-tools-lab cycle \
  --config configs/nucleo_f411re.yaml \
  --image firmware/bad_image/bad_image.bin

# Inspect the report
cat output/nucleo_f411re_*.txt

# Document findings in docs/triage_playbook.md
```

Use the failure decision tree in `docs/triage_playbook.md` to classify
whether this is a flash-layer or firmware-layer failure.
