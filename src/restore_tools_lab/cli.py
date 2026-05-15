"""Command-line interface for restore-tools-lab."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from restore_tools_lab import __version__
from restore_tools_lab.config import BoardConfig, ConfigError
from restore_tools_lab.flash_utils import FlashError, flash_image
from restore_tools_lab.report_utils import CycleRecord, write_csv_record, write_text_report
from restore_tools_lab.serial_utils import SerialError, capture_serial
from restore_tools_lab.verify_utils import VerifyError, verify_boot


# --------------------------------------------------------------------------- #
# Logging setup
# --------------------------------------------------------------------------- #


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    fmt = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, stream=sys.stderr)


# --------------------------------------------------------------------------- #
# Argument parser
# --------------------------------------------------------------------------- #


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="restore-tools-lab",
        description="Embedded restore-tools lab for STM32 boards.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--version", action="version", version=f"restore-tools-lab {__version__}"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging."
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ---- flash ------------------------------------------------------------ #
    p_flash = sub.add_parser("flash", help="Flash a firmware image to the board.")
    p_flash.add_argument("--config", required=True, help="Path to board YAML config.")
    p_flash.add_argument("--image", required=True, help="Path to .bin firmware image.")
    p_flash.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the flash command without executing it.",
    )

    # ---- log -------------------------------------------------------------- #
    p_log = sub.add_parser("log", help="Capture serial output to a file.")
    p_log.add_argument("--config", required=True, help="Path to board YAML config.")
    p_log.add_argument(
        "--duration",
        type=float,
        default=None,
        help="Seconds to capture (default: config timeout_sec).",
    )
    p_log.add_argument(
        "--output",
        default=None,
        help="Path for the output log file.",
    )

    # ---- verify ----------------------------------------------------------- #
    p_verify = sub.add_parser(
        "verify",
        help="Open serial port and confirm the board prints the boot marker.",
    )
    p_verify.add_argument("--config", required=True, help="Path to board YAML config.")
    p_verify.add_argument(
        "--timeout",
        type=float,
        default=None,
        help="Override the boot-marker wait timeout.",
    )

    # ---- cycle ------------------------------------------------------------ #
    p_cycle = sub.add_parser(
        "cycle",
        help="Flash image, verify boot marker, write result record.",
    )
    p_cycle.add_argument("--config", required=True, help="Path to board YAML config.")
    p_cycle.add_argument("--image", required=True, help="Path to .bin firmware image.")
    p_cycle.add_argument(
        "--output-dir",
        default="output/csv",
        help="Directory to write result CSV (default: output/csv).",
    )
    p_cycle.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run flash (skip actual flashing); still attempts verify.",
    )

    return parser


# --------------------------------------------------------------------------- #
# Sub-command handlers
# --------------------------------------------------------------------------- #


def _cmd_flash(args: argparse.Namespace, cfg: BoardConfig) -> int:
    try:
        result = flash_image(cfg, args.image, dry_run=args.dry_run)
    except FlashError as exc:
        logging.getLogger(__name__).error("Flash error: %s", exc)
        return 1

    print(result)
    return 0 if result.success else 1


def _cmd_log(args: argparse.Namespace, cfg: BoardConfig) -> int:
    # Build a sensible default output path from the board name.
    output_path: str | Path | None = args.output
    if output_path is None:
        output_path = Path("logs") / "raw" / f"{cfg.board_name}.log"

    try:
        result = capture_serial(cfg, duration_sec=args.duration, output_path=output_path)
    except Exception as exc:
        logging.getLogger(__name__).error("Serial error: %s", exc)
        return 1

    print(f"Captured {len(result)} lines from {cfg.serial_port} → {output_path}")
    return 0


def _cmd_verify(args: argparse.Namespace, cfg: BoardConfig) -> int:
    try:
        result = verify_boot(cfg, timeout_sec=args.timeout)
    except VerifyError as exc:
        logging.getLogger(__name__).error("Verify error: %s", exc)
        return 1

    print(result)
    return 0 if result.passed else 1


def _cmd_cycle(args: argparse.Namespace, cfg: BoardConfig) -> int:
    log = logging.getLogger(__name__)
    error_msg = ""
    flash_rc = 0
    flash_ok = False
    verify_ok = False
    lines_count = 0

    # Step 1: Flash --------------------------------------------------------- #
    try:
        flash_result = flash_image(cfg, args.image, dry_run=args.dry_run)
        flash_ok = flash_result.success
        flash_rc = flash_result.returncode
        if not flash_ok:
            error_msg = f"Flash failed (rc={flash_rc})"
            log.error("[%s] %s", cfg.board_name, error_msg)
    except FlashError as exc:
        error_msg = str(exc)
        log.error("[%s] Flash error: %s", cfg.board_name, exc)

    # Step 2: Verify boot marker -------------------------------------------- #
    if flash_ok or args.dry_run:
        try:
            verify_result = verify_boot(cfg)
            verify_ok = verify_result.passed
            lines_count = len(verify_result.lines_received)
            if not verify_ok and not error_msg:
                error_msg = "Boot marker not found within timeout."
        except VerifyError as exc:
            error_msg = str(exc)
            log.error("[%s] Verify error: %s", cfg.board_name, exc)

    # Step 3: Record result ------------------------------------------------- #
    record = CycleRecord.now(
        board_name=cfg.board_name,
        image_path=str(args.image),
        flash_success=flash_ok,
        flash_returncode=flash_rc,
        verify_passed=verify_ok,
        boot_marker=cfg.boot_marker,
        lines_received=lines_count,
        error=error_msg,
    )

    csv_path = write_csv_record(record, csv_dir=args.output_dir)
    report_path = write_text_report(record)

    status = "PASS" if record.overall_pass else "FAIL"
    print(f"Cycle {status} — {cfg.board_name}")
    print(f"  CSV    : {csv_path}")
    print(f"  Report : {report_path}")

    return 0 if record.overall_pass else 1


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #


COMMAND_MAP = {
    "flash": _cmd_flash,
    "log": _cmd_log,
    "verify": _cmd_verify,
    "cycle": _cmd_cycle,
}


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose)

    # Load config (shared by all sub-commands).
    try:
        cfg = BoardConfig.from_file(args.config)
    except ConfigError as exc:
        logging.getLogger(__name__).error("Config error: %s", exc)
        return 2

    handler = COMMAND_MAP.get(args.command)
    if handler is None:
        parser.print_help()
        return 2

    return handler(args, cfg)


if __name__ == "__main__":
    sys.exit(main())
