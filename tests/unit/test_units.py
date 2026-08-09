import pytest
from pvt.core import units as u

@pytest.mark.parametrize("fwd,back,value", [
    (u.f_to_r, u.r_to_f, 256.0), (u.f_to_c, u.c_to_f, 118.0),
    (u.c_to_k, u.k_to_c, 20.0), (u.bara_to_psia, u.psia_to_bara, 5.5),
    (u.scf_stb_to_cc_cc, u.cc_cc_to_scf_stb, 339.0),
    (u.scf_to_cc, u.cc_to_scf, 0.12731), (u.stb_to_cc, u.cc_to_stb, 1.0),
])
def test_round_trip(fwd, back, value):
    assert back(fwd(value)) == pytest.approx(value, rel=1e-12)

def test_known_values():
    assert u.f_to_r(60.0) == pytest.approx(519.67)
    assert u.f_to_k(60.0) == pytest.approx(288.7056, rel=1e-6)
    assert u.psig_to_psia(1156.0) == pytest.approx(1170.696)
    assert u.psia_to_psig(1170.696) == pytest.approx(1156.0)
    assert u.mbar_to_psia(1015.5981) == pytest.approx(14.73, rel=1e-6)
    assert u.api_from_density_g_cc(0.870056) == pytest.approx(31.133, abs=0.01)
    assert u.density_g_cc_from_api(31.133) == pytest.approx(0.870056, abs=1e-4)
    assert u.scf_stb_to_cc_cc(339.0) == pytest.approx(60.378, abs=0.001)  # LiveOil B25
    assert u.sg_from_density_g_cc(0.9991) == pytest.approx(1.0, rel=1e-6)  # water @ 60F
