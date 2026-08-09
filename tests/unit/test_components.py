import pytest
from pvt.core.components import KATZ_FIROOZABADI as KF


def test_library_size_and_order():
    assert len(KF.codes) == 52
    assert KF.codes[0] == "H2" and KF.codes[-1] == "C36+"


def test_known_properties():
    c1 = KF.get("C1")
    assert c1.mw == pytest.approx(16.043)
    assert c1.tc_r == pytest.approx(343.0, abs=1.0)
    assert KF.get("C7").mw == pytest.approx(100.204)
    assert KF.get("C36+").mw == pytest.approx(636.4)
    assert KF.get("Toluene").liquid_density_g_cc == pytest.approx(0.8718)


def test_molar_volume():
    c = KF.get("C6")
    assert c.molar_volume_cc == pytest.approx(c.mw / c.liquid_density_g_cc)


def test_c36_override_is_isolated_copy():
    lib2 = KF.with_c36_mw(635.0)
    assert lib2.get("C36+").mw == 635.0
    assert KF.get("C36+").mw == pytest.approx(636.4)
    assert lib2.get("C1") is KF.get("C1")


def test_unknown_code_raises():
    with pytest.raises(KeyError):
        KF.get("C99")
