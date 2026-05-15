"""Report utilities: write cycle results to CSV and human-readable text."""

from __future__ import annotations

import csv
import logging
import textwrap
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default output locations
DEFAULT_CSV_DIR = Path("output/csv")
DEFAULT_REPORT_DIR = Path("output")


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #


@dataclass
class CycleRecord:
    """One row written to the CSV result log."""

    timestamp: str
    board_name: str
    image_path: str
    flash_success: bool
    flash_returncode: int
    verify_passed: bool
    boot_marker: str
    lines_received: int
    error: str = ""

    # Convenience constructors -----------------------------------------------

    @classmethod
    def now(
        cls,
        board_name: str,
        image_path: str,
        flash_success: bool,
        flash_returncode: int,
        verify_passed: bool,
        boot_marker: str,
        lines_received: int,
        error: str = "",
    ) -> "CycleRecord":
        """Create a record stamped with the current UTC time."""
        ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return cls(
            timestamp=ts,
            board_name=board_name,
            image_path=image_path,
            flash_success=flash_success,
            flash_returncode=flash_returncode,
            verify_passed=verify_passed,
            boot_marker=boot_marker,
            lines_received=lines_received,
            error=error,
        )

    @property
    def overall_pass(self) -> bool:
        return self.flash_success and self.verify_passed


# --------------------------------------------------------------------------- #
# Writers
# --------------------------------------------------------------------------- #


def write_csv_record(
    record: CycleRecord,
    csv_dir: str | Path | None = None,
) -> Path:
    """
    Append *record* to a per-board CSV file in *csv_dir*.

    The file is created with headers if it does not already exist.

    Args:
        record:  CycleRecord to write.
        csv_dir: Directory to write CSV files to (default: output/csv/).

    Returns:
        Path of the CSV file written.
    """
    out_dir = Path(csv_dir) if csv_dir else DEFAULT_CSV_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path = out_dir / f"{record.board_name}_results.csv"
    fields = list(asdict(record).keys())
    file_exists = csv_path.exists()

    with csv_path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        if not file_exists:
            writer.writeheader()
        writer.writerow(asdict(record))

    logger.info("Result appended to %s", csv_path)
    return csv_path


def write_text_report(
    record: CycleRecord,
    report_dir: str | Path | None = None,
) -> Path:
    """
    Write a human-readable triage report for a single cycle run.

    Args:
        record:     CycleRecord describing the outcome.
        report_dir: Directory to write the report to (default: output/).

    Returns:
        Path of the report file written.
    """
    out_dir = Path(report_dir) if report_dir else DEFAULT_REPORT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    safe_ts = record.timestamp.replace(":", "").replace("-", "")
    report_path = out_dir / f"{record.board_name}_{safe_ts}.txt"

    status = "PASS" if record.overall_pass else "FAIL"
    lines = [
        "=" * 60,
        f"Cycle Report — {record.board_name}",
        f"Timestamp : {record.timestamp}",
        f"Overall   : {status}",
        "=" * 60,
        "",
        "[Flash]",
        f"  Image       : {record.image_path}",
        f"  Success     : {record.flash_success}",
        f"  Return code : {record.flash_returncode}",
        "",
        "[Verify]",
        f"  Boot marker : {record.boot_marker!r}",
        f"  Passed      : {record.verify_passed}",
        f"  Lines recv  : {record.lines_received}",
        "",
    ]
    if record.error:
        lines += ["[Error]", f"  {record.error}", ""]

    if not record.overall_pass:
        lines += [
            "[Triage Hint]",
            *textwrap.wrap(
                _triage_hint(record),
                width=56,
                initial_indent="  ",
                subsequent_indent="  ",
            ),
            "",
        ]

    lines.append("=" * 60)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("Text report written to %s", report_path)
    return report_path


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _triage_hint(record: CycleRecord) -> str:
    """Return a short triage suggestion based on what failed."""
    if not record.flash_success:
        return (
            "Flash failed. Check: STM32_Programmer_CLI on PATH, SWD cable connected, "
            "board powered, image path is valid. See docs/failure_modes.md."
        )
    if not record.verify_passed:
        return (
            "Flash succeeded but boot marker was not received. Check: correct serial "
            "port, correct baud rate, firmware prints the expected marker string, "
            "reset timing. See docs/triage_playbook.md."
        )
    return "Cycle failed for an unknown reason. Check error field and logs."
