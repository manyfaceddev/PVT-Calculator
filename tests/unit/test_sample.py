"""Tests for Sample, CrossRef, and Study dataclasses."""
from pvt.core.sample import CrossRef, Sample, Study


def test_cross_ref_provenance():
    psat = CrossRef(value=1156.0, source_test="CCE", source_field="psat_psig")
    study = Study(
        sample=Sample(
            sample_id="SA-372",
            well="WELL-X",
            field_name="Upper Zakum",
            reservoir="Kharaib-2",
            depth_ft_md=9105.0,
            fluid_type="Black Oil",
            cylinder="RF1168636",
        ),
        reservoir_p_psig=3939.0,
        reservoir_t_f=256.0,
        psat=psat,
    )
    assert study.psat.value == 1156.0
    assert study.psat.source_test == "CCE"
