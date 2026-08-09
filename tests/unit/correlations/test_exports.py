"""Import-surface tests: each correlations subpackage must expose its modules
as attributes (`from pvt.correlations.<subpkg> import <module>` /
`pvt.correlations.<subpkg>.<module>`), and the bubble_point package must NOT
carry an ambiguous bare `bubble_point` name (four different correlations
live there -- see pvt/correlations/bubble_point/__init__.py)."""

import pvt.correlations.bubble_point as bubble_point_pkg
import pvt.correlations.pseudocritical as pseudocritical
import pvt.correlations.viscosity as viscosity
import pvt.correlations.zfactor as zfactor


def test_pseudocritical_exposes_its_modules():
    for name in ("erbar", "piper_mccain", "sbv", "sutton", "wichert_aziz"):
        assert hasattr(pseudocritical, name), f"pseudocritical missing {name}"


def test_zfactor_exposes_its_modules():
    for name in ("dak", "hall_yarborough"):
        assert hasattr(zfactor, name), f"zfactor missing {name}"


def test_viscosity_exposes_its_modules():
    for name in ("critical_volumes", "jossi_stiel_thodos", "lee_gonzalez_eakin"):
        assert hasattr(viscosity, name), f"viscosity missing {name}"


def test_bubble_point_exposes_its_modules():
    for name in ("almarhoun", "glaso", "standing", "vasquez_beggs"):
        assert hasattr(bubble_point_pkg, name), f"bubble_point missing {name}"


def test_bubble_point_deprecated_alias_still_works():
    # standing_bubble_point keeps working from the package level -- existing callers
    # (ui/recombination.py, cli.py) import it as `from pvt.correlations.bubble_point
    # import standing_bubble_point` / `from pvt import standing_bubble_point`.
    assert hasattr(bubble_point_pkg, "standing_bubble_point")
    from pvt import standing_bubble_point
    assert standing_bubble_point is bubble_point_pkg.standing_bubble_point


def test_bubble_point_has_no_ambiguous_bare_name():
    # Four independent correlations (almarhoun, glaso, standing, vasquez_beggs) each
    # define their own bubble_point() -- a package-level bare `bubble_point` name
    # would be ambiguous among them, so it must not be re-exported.
    assert not hasattr(bubble_point_pkg, "bubble_point")
