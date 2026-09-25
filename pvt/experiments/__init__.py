"""
pvt/experiments — Laboratory experiment calculation modules.

Each submodule owns one experiment type end-to-end (models, calc, validate)
over the shared pvt.core primitives (CompositionStream, ComponentLibrary,
units, exceptions).

Modules
-------
pvt.experiments.flash           Single-stage atmospheric flash volumetrics
pvt.experiments.recombination   Separator recombination calculations
pvt.experiments.cce             Constant Composition Expansion

Planned modules
----------------
pvt.experiments.cvd               Constant Volume Depletion
pvt.experiments.differential_liberation
"""
