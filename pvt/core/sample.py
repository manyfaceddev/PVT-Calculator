"""Sample and Study dataclasses for PVT calculations.

CrossRef bridges upstream test results consumed downstream with provenance,
replacing manual retyping between workbooks. Units are carried in source_field names.
"""
from dataclasses import dataclass


@dataclass
class CrossRef:
    """Cross-reference to an upstream test result with full provenance."""

    value: float
    source_test: str
    source_field: str
    note: str = ""


@dataclass
class Sample:
    """A fluid sample from a well."""

    sample_id: str
    well: str
    field_name: str
    reservoir: str
    depth_ft_md: float | None
    fluid_type: str
    cylinder: str
    client: str = ""
    project: str = ""


@dataclass
class Study:
    """A PVT study containing a sample and its measured or derived properties."""

    sample: Sample
    reservoir_p_psig: float | None = None
    reservoir_t_f: float | None = None
    psat: CrossRef | None = None
    density_at_psat: CrossRef | None = None
    rs_flash: CrossRef | None = None
    bo_flash: CrossRef | None = None
