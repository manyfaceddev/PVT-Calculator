import pytest

from pvt.core.exceptions import InputValidationError
from pvt.correlations.viscosity.critical_volumes import VC_TABLE, vc_mix


# --- Table-vs-VBA spot values -------------------------------------------------
# docs/reference/gasprop_functions.bas, CalculateCriticals (lines ~437-444):
#   crit_vc = Array(1.44, 1.59, 1.51, 2.37, 1.565, 3.21, _
#                   4.21, 4.08, 4.9, 4.87, 5.93, C7plusVC)
# in positional order N2, C1, CO2, C2, H2S, C3, iC4, nC4, iC5, nC5, C6, C7+
# (confirmed against the parallel mol_wt array at the same lines: 28.016=N2,
# 16.042=C1, 44.01=CO2, 30.068=C2, 34.076=H2S, 44.094=C3, 58.12=iC4/nC4,
# 72.146=iC5/nC5, 86.172=C6).

@pytest.mark.parametrize("code, expected", [
    ("N2", 1.44),
    ("C1", 1.59),
    ("CO2", 1.51),
    ("C2", 2.37),
    ("H2S", 1.565),
    ("C3", 3.21),
    ("iC4", 4.21),
    ("nC4", 4.08),
    ("iC5", 4.9),
    ("nC5", 4.87),
    ("C6", 5.93),
])
def test_table_matches_vba_spot_values(code, expected):
    assert VC_TABLE[code] == expected


def test_table_has_exactly_eleven_entries_no_c7_plus():
    # C7+ is deliberately excluded from VC_TABLE -- it's supplied per-call via
    # vc_mix's c7_plus_vc argument (from erbar.c7_plus_criticals), not looked up here.
    assert len(VC_TABLE) == 11
    assert "C7+" not in VC_TABLE


# --- Pure-component identity --------------------------------------------------

@pytest.mark.parametrize("code", list(VC_TABLE))
def test_pure_component_identity(code):
    assert vc_mix({code: 1.0}) == pytest.approx(VC_TABLE[code], rel=1e-12)


def test_pure_c7_plus_identity():
    assert vc_mix({"C7+": 1.0}, c7_plus_vc=13.896579108178768) == pytest.approx(
        13.896579108178768, rel=1e-12)


# --- Mole-fraction-weighted mixing --------------------------------------------

def test_mole_fraction_weighted_mix():
    mol_fractions = {"C1": 0.90, "C2": 0.05, "CO2": 0.03, "C7+": 0.02}
    c7_plus_vc = 13.896579108178768
    expected = (
        0.90 * VC_TABLE["C1"] + 0.05 * VC_TABLE["C2"] + 0.03 * VC_TABLE["CO2"]
        + 0.02 * c7_plus_vc
    )
    assert vc_mix(mol_fractions, c7_plus_vc=c7_plus_vc) == pytest.approx(expected, rel=1e-12)


def test_c7_plus_vc_ignored_without_c7_plus_key():
    # c7_plus_vc has no effect when mol_fractions has no "C7+" key.
    a = vc_mix({"C1": 1.0}, c7_plus_vc=999.0)
    b = vc_mix({"C1": 1.0}, c7_plus_vc=0.0)
    assert a == b


# --- Unknown-key guard ---------------------------------------------------------

def test_unknown_key_raises():
    with pytest.raises(InputValidationError):
        vc_mix({"XYZ": 1.0})


def test_unknown_key_raises_alongside_known_keys():
    with pytest.raises(InputValidationError):
        vc_mix({"C1": 0.9, "Bogus": 0.1})
