"""
tests/unit/test_cli.py — Tests for `cli.py` (Task 12).

`cli.py` sits outside the `pvt` coverage gate (pyproject's `--cov=pvt`); these
tests prove `flash --workbook <path>` reproduces the SA-372 golden numbers
end to end (import -> calculate -> recombine_mass -> printed report,
brief's Step-1 contract verbatim) and that `recombine` still works on the
pre-Task-12 CLI surface, now living under its own subcommand.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cli import main

FLASH_WB = Path("tests/fixtures/workbooks/ADRIC_Flash_Separation_Calc_v6.1.xlsx")


def test_cli_flash_on_fixture(capsys):
    """Brief's Step-1 test, verbatim."""
    main(["flash", "--workbook", str(FLASH_WB)])
    out = capsys.readouterr().out
    assert "335.13" in out and "SA-372" in out


def test_cli_flash_missing_workbook_reports_error(capsys):
    rc = main(["flash", "--workbook", "tests/fixtures/workbooks/does_not_exist.xlsx"])
    assert rc != 0


def test_cli_flash_wrong_workbook_reports_validation_error(capsys):
    """Pointing --workbook at the LiveOil (not Flash) template surfaces
    flash_v61.read's InputValidationError as a CLI error line, not a raw
    traceback."""
    wrong_wb = Path("tests/fixtures/workbooks/ADRIC_LiveOil_Preparation_Calc_v4.1.xlsx")
    rc = main(["flash", "--workbook", str(wrong_wb)])
    captured = capsys.readouterr()
    assert rc == 1
    assert not captured.out
    assert "error:" in captured.err


def test_cli_recombine_single_stage_field_units(capsys):
    """The pre-Task-12 CLI surface (single-stage, field units) still works,
    now under the `recombine` subcommand."""
    rc = main([
        "recombine",
        "--gor", "850", "--p_sep", "815", "--t_sep", "145", "--z_sep", "0.855",
        "--v_live", "300", "--p_recomb", "5014.7", "--t_recomb", "200", "--z_recomb", "0.820",
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "RESULTS REPORT" in out
    assert "Cylinder Mix Ratio" in out
    # Demo-minor fix: the footer previously stated 14.696 psia (the
    # gas-constant/psig->psia basis, P_ATM_PSIA) as "standard conditions",
    # but this report's own volumetrics are on the lab's 14.73 psia basis
    # (pvt.core.constants.P_STD_PSIA) -- the footer must say so.
    assert "14.73 psia" in out
    assert "14.696" not in out


def test_cli_recombine_two_stage_missing_args_errors(capsys):
    rc = main([
        "recombine",
        "--gor", "800", "--p_sep", "800", "--t_sep", "140", "--z_sep", "0.865",
        "--stages", "2",
        "--v_live", "300", "--p_recomb", "5014.7", "--t_recomb", "200", "--z_recomb", "0.820",
    ])
    err = capsys.readouterr().err
    assert rc == 1
    assert "--gor2" in err


def test_cli_recombine_invalid_inputs_errors(capsys):
    rc = main([
        "recombine",
        "--gor", "-1", "--p_sep", "815", "--t_sep", "145", "--z_sep", "0.855",
        "--v_live", "300", "--p_recomb", "5014.7", "--t_recomb", "200", "--z_recomb", "0.820",
    ])
    err = capsys.readouterr().err
    assert rc == 1
    assert "error:" in err


def test_cli_requires_a_subcommand():
    with pytest.raises(SystemExit):
        main([])
