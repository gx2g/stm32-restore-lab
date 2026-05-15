"""Tests for restore_tools_lab.report_utils."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from restore_tools_lab.report_utils import (
    CycleRecord,
    write_csv_record,
    write_text_report,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def make_record(
    board: str = "nucleo_f411re",
    flash_success: bool = True,
    verify_passed: bool = True,
    flash_rc: int = 0,
    error: str = "",
) -> CycleRecord:
    return CycleRecord.now(
        board_name=board,
        image_path="firmware/blink/blink.bin",
        flash_success=flash_success,
        flash_returncode=flash_rc,
        verify_passed=verify_passed,
        boot_marker="BOOT_OK",
        lines_received=3,
        error=error,
    )


# --------------------------------------------------------------------------- #
# CycleRecord
# --------------------------------------------------------------------------- #


def test_cycle_record_overall_pass():
    r = make_record(flash_success=True, verify_passed=True)
    assert r.overall_pass is True


def test_cycle_record_flash_fail():
    r = make_record(flash_success=False, verify_passed=False)
    assert r.overall_pass is False


def test_cycle_record_verify_fail():
    r = make_record(flash_success=True, verify_passed=False)
    assert r.overall_pass is False


def test_cycle_record_timestamp_format():
    r = make_record()
    # ISO 8601 UTC stamp ends with Z
    assert r.timestamp.endswith("Z")
    assert "T" in r.timestamp


def test_cycle_record_board_name_stored():
    r = make_record(board="bl475e_iot01a")
    assert r.board_name == "bl475e_iot01a"


# --------------------------------------------------------------------------- #
# write_csv_record
# --------------------------------------------------------------------------- #


def test_write_csv_creates_file(tmp_path: Path):
    r = make_record()
    path = write_csv_record(r, csv_dir=tmp_path)
    assert path.exists()


def test_write_csv_filename_includes_board(tmp_path: Path):
    r = make_record(board="nucleo_f411re")
    path = write_csv_record(r, csv_dir=tmp_path)
    assert "nucleo_f411re" in path.name


def test_write_csv_has_header(tmp_path: Path):
    r = make_record()
    path = write_csv_record(r, csv_dir=tmp_path)
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert "board_name" in rows[0]
    assert "flash_success" in rows[0]
    assert "verify_passed" in rows[0]


def test_write_csv_appends_multiple_records(tmp_path: Path):
    r1 = make_record(board="nucleo_f411re", flash_success=True, verify_passed=True)
    r2 = make_record(board="nucleo_f411re", flash_success=True, verify_passed=False)
    write_csv_record(r1, csv_dir=tmp_path)
    write_csv_record(r2, csv_dir=tmp_path)
    path = tmp_path / "nucleo_f411re_results.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert len(rows) == 2


def test_write_csv_header_written_once(tmp_path: Path):
    for _ in range(3):
        write_csv_record(make_record(), csv_dir=tmp_path)
    path = tmp_path / "nucleo_f411re_results.csv"
    lines = path.read_text(encoding="utf-8").splitlines()
    header_count = sum(1 for l in lines if "board_name" in l)
    assert header_count == 1


def test_write_csv_separate_files_per_board(tmp_path: Path):
    write_csv_record(make_record(board="nucleo_f411re"), csv_dir=tmp_path)
    write_csv_record(make_record(board="bl475e_iot01a"), csv_dir=tmp_path)
    assert (tmp_path / "nucleo_f411re_results.csv").exists()
    assert (tmp_path / "bl475e_iot01a_results.csv").exists()


def test_write_csv_creates_parent_dirs(tmp_path: Path):
    nested = tmp_path / "deep" / "nested"
    write_csv_record(make_record(), csv_dir=nested)
    assert nested.exists()


# --------------------------------------------------------------------------- #
# write_text_report
# --------------------------------------------------------------------------- #


def test_write_text_report_creates_file(tmp_path: Path):
    r = make_record()
    path = write_text_report(r, report_dir=tmp_path)
    assert path.exists()


def test_write_text_report_pass_contains_pass(tmp_path: Path):
    r = make_record(flash_success=True, verify_passed=True)
    path = write_text_report(r, report_dir=tmp_path)
    assert "PASS" in path.read_text(encoding="utf-8")


def test_write_text_report_fail_contains_fail(tmp_path: Path):
    r = make_record(flash_success=False, verify_passed=False, flash_rc=1)
    path = write_text_report(r, report_dir=tmp_path)
    assert "FAIL" in path.read_text(encoding="utf-8")


def test_write_text_report_contains_board_name(tmp_path: Path):
    r = make_record(board="bl475e_iot01a")
    path = write_text_report(r, report_dir=tmp_path)
    assert "bl475e_iot01a" in path.read_text(encoding="utf-8")


def test_write_text_report_contains_triage_hint_on_flash_fail(tmp_path: Path):
    r = make_record(flash_success=False, verify_passed=False, flash_rc=1)
    path = write_text_report(r, report_dir=tmp_path)
    assert "Triage Hint" in path.read_text(encoding="utf-8")


def test_write_text_report_contains_triage_hint_on_verify_fail(tmp_path: Path):
    r = make_record(flash_success=True, verify_passed=False)
    path = write_text_report(r, report_dir=tmp_path)
    assert "Triage Hint" in path.read_text(encoding="utf-8")


def test_write_text_report_no_triage_hint_on_pass(tmp_path: Path):
    r = make_record(flash_success=True, verify_passed=True)
    path = write_text_report(r, report_dir=tmp_path)
    assert "Triage Hint" not in path.read_text(encoding="utf-8")


def test_write_text_report_contains_error_section(tmp_path: Path):
    r = make_record(flash_success=False, error="SWD connection failed")
    path = write_text_report(r, report_dir=tmp_path)
    assert "SWD connection failed" in path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# Both boards parametrised (uses conftest any_board_cfg indirectly)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("board", ["nucleo_f411re", "bl475e_iot01a"])
def test_csv_and_report_for_both_boards(tmp_path: Path, board: str):
    r = make_record(board=board)
    csv_path = write_csv_record(r, csv_dir=tmp_path / "csv")
    rpt_path = write_text_report(r, report_dir=tmp_path / "reports")
    assert csv_path.exists()
    assert rpt_path.exists()
    assert board in csv_path.read_text(encoding="utf-8")
    assert board in rpt_path.read_text(encoding="utf-8")
