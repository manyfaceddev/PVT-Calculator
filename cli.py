#!/usr/bin/env python3
"""
cli.py — Command-line interface for PVT Separator Recombination Calculator.

Usage examples:
  # Single stage (field units)
  python cli.py --gor 850 --p_sep 815 --t_sep 145 --z_sep 0.855 \\
                --v_live 300 --p_recomb 5014.7 --t_recomb 200 --z_recomb 0.820

  # Two-stage with Pb estimate
  python cli.py --gor 850 --p_sep 800 --t_sep 140 --z_sep 0.865 \\
                --stages 2 --gor2 50 --p2 65 --t2 100 --z2 0.977 \\
                --v_live 300 --p_recomb 5014.7 --t_recomb 200 --z_recomb 0.820 \\
                --api 42 --sg_gas 0.72

  # SI units
  python cli.py --units si --gor 151.4 --p_sep 55.8 --t_sep 62.8 --z_sep 0.865 \\
                --v_live 300 --p_recomb 346.7 --t_recomb 93.3 --z_recomb 0.820
"""

import argparse
import sys

from pvt import (
    SeparatorStage,
    calculate_multistage,
    validate_multistage,
    standing_bubble_point,
    SCF_STB_TO_CC_CC,
    BARA_TO_PSIA,
)

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cli.py",
        description="PVT Separator Recombination Calculator — command-line interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # ── Stage 1 (required) ──────────────────────────────────────────────────
    g1 = p.add_argument_group("Stage 1 — separator conditions (required)")
    g1.add_argument("--gor",   type=float, required=True,
                    metavar="GOR",
                    help="Stage 1 GOR (scf/STB for field units, sm³/sm³ for SI)")
    g1.add_argument("--p_sep", type=float, required=True,
                    metavar="PSIA_or_BARA",
                    help="Stage 1 separator pressure (psia or bara)")
    g1.add_argument("--t_sep", type=float, required=True,
                    metavar="F_or_C",
                    help="Stage 1 separator temperature (°F or °C)")
    g1.add_argument("--z_sep", type=float, required=True,
                    metavar="Z",
                    help="Stage 1 Z-factor of separator gas (dimensionless)")

    # ── Stage 2 (optional) ──────────────────────────────────────────────────
    g2 = p.add_argument_group("Stage 2 inputs (required when --stages 2 or 3)")
    g2.add_argument("--gor2", type=float, metavar="GOR2",   help="Stage 2 GOR")
    g2.add_argument("--p2",   type=float, metavar="PSIA2",  help="Stage 2 pressure")
    g2.add_argument("--t2",   type=float, metavar="F2",     help="Stage 2 temperature")
    g2.add_argument("--z2",   type=float, metavar="Z2",     help="Stage 2 Z-factor")

    # ── Stage 3 (optional) ──────────────────────────────────────────────────
    g3 = p.add_argument_group("Stage 3 inputs (required when --stages 3)")
    g3.add_argument("--gor3", type=float, metavar="GOR3",   help="Stage 3 GOR")
    g3.add_argument("--p3",   type=float, metavar="PSIA3",  help="Stage 3 pressure")
    g3.add_argument("--t3",   type=float, metavar="F3",     help="Stage 3 temperature")
    g3.add_argument("--z3",   type=float, metavar="Z3",     help="Stage 3 Z-factor")

    # ── Live fluid & recombination conditions ────────────────────────────────
    gc = p.add_argument_group("Live fluid & recombination conditions")
    gc.add_argument("--v_live",   type=float, required=True, metavar="CC",
                    help="Volume of live fluid to prepare (cc)")
    gc.add_argument("--p_recomb", type=float, required=True, metavar="PSIA_or_BARA",
                    help="Recombination (charging) pressure (psia or bara)")
    gc.add_argument("--t_recomb", type=float, required=True, metavar="F_or_C",
                    help="Recombination (charging) temperature (°F or °C)")
    gc.add_argument("--z_recomb", type=float, default=1.0, metavar="Z",
                    help="Z-factor of gas at recombination P & T (default: 1.0)")
    gc.add_argument("--bo_sep",   type=float, default=1.00,  metavar="BO",
                    help="Oil FVF at separator conditions (default: 1.00)")
    gc.add_argument("--stages",   type=int,   default=1, choices=[1, 2, 3],
                    metavar="{1,2,3}",
                    help="Number of separator stages (default: 1)")

    # ── Optional Pb inputs ───────────────────────────────────────────────────
    gpb = p.add_argument_group(
        "Standing's Pb estimate (both --api and --sg_gas required to activate)"
    )
    gpb.add_argument("--api",    type=float, metavar="API",
                     help="Stock-tank oil API gravity (°API)")
    gpb.add_argument("--sg_gas", type=float, metavar="SG",
                     help="Weighted-average gas specific gravity (air = 1.0)")
    gpb.add_argument("--t_res",  type=float, metavar="F_or_C",
                     help=(
                         "Reservoir temperature for Pb estimation "
                         "(defaults to Stage 1 temperature if omitted)"
                     ))

    # ── Units ────────────────────────────────────────────────────────────────
    p.add_argument("--units", choices=["field", "si"], default="field",
                   help="Unit system: 'field' (psia/°F/scf/STB) or 'si' (bara/°C/sm³/sm³) "
                        "(default: field)")

    return p


# ---------------------------------------------------------------------------
# Report formatting helpers
# ---------------------------------------------------------------------------

_COL = 26   # label column width
_W   = 52   # total line width (inside borders)

def _rule(char: str = "=") -> str:
    return char * (_W + 4)


def _row(label: str, value: str) -> str:
    return f"  {label:<{_COL}}: {value}"


def _section(title: str) -> str:
    pad = (_W - len(title)) // 2
    return f"\n{'─' * (pad + 2)} {title} {'─' * (_W - pad - len(title) + 2)}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = build_parser()
    args   = parser.parse_args()

    units = args.units

    # ── Build stage list ─────────────────────────────────────────────────────
    STAGE_LABELS = {
        1: ["Separator"],
        2: ["HP Separator", "LP Separator"],
        3: ["HP Separator", "MP Separator", "LP Separator"],
    }
    labels = STAGE_LABELS[args.stages]

    stages = [
        SeparatorStage(R=args.gor, P=args.p_sep, T=args.t_sep, Z=args.z_sep,
                       label=labels[0])
    ]

    if args.stages >= 2:
        missing = [f for f, v in [("--gor2", args.gor2), ("--p2", args.p2),
                                   ("--t2", args.t2),    ("--z2", args.z2)] if v is None]
        if missing:
            print(f"error: --stages 2 requires {', '.join(missing)}", file=sys.stderr)
            return 1
        stages.append(SeparatorStage(R=args.gor2, P=args.p2, T=args.t2, Z=args.z2,
                                     label=labels[1]))

    if args.stages == 3:
        missing = [f for f, v in [("--gor3", args.gor3), ("--p3", args.p3),
                                   ("--t3", args.t3),    ("--z3", args.z3)] if v is None]
        if missing:
            print(f"error: --stages 3 requires {', '.join(missing)}", file=sys.stderr)
            return 1
        stages.append(SeparatorStage(R=args.gor3, P=args.p3, T=args.t3, Z=args.z3,
                                     label=labels[2]))

    # ── Validate ─────────────────────────────────────────────────────────────
    errors = validate_multistage(
        stages, args.v_live, args.bo_sep,
        args.p_recomb, args.t_recomb, args.z_recomb, units,
    )
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        return 1

    # ── Calculate ────────────────────────────────────────────────────────────
    res = calculate_multistage(
        stages, args.v_live, args.bo_sep,
        args.p_recomb, args.t_recomb, args.z_recomb, units,
    )

    # ── Unit labels ──────────────────────────────────────────────────────────
    if units == "field":
        gor_unit  = "scf/STB"
        pres_unit = "psia"
        temp_unit = "°F"
        gas_unit  = "scf"
    else:
        gor_unit  = "sm³/sm³"
        pres_unit = "bara"
        temp_unit = "°C"
        gas_unit  = "sm³"

    gor_err_pct = (
        abs(res.GOR_check - res.R_total_input) / res.R_total_input * 100
        if res.R_total_input > 0 else 0.0
    )
    gor_ok = "✓" if gor_err_pct < 0.1 else "⚠  deviation {:.3f}%".format(gor_err_pct)

    # ── Pb estimate ──────────────────────────────────────────────────────────
    pb_line: str | None = None
    if args.api is not None and args.sg_gas is not None:
        if units == "field":
            R_for_pb = res.R_total_input
            T_for_pb = args.t_res if args.t_res is not None else args.t_sep
        else:
            R_for_pb = res.R_total_input / SCF_STB_TO_CC_CC
            T_for_pb = (
                (args.t_res * 9 / 5 + 32.0)
                if args.t_res is not None
                else (args.t_sep * 9 / 5 + 32.0)
            )
        Pb_psia = standing_bubble_point(R_for_pb, args.sg_gas, T_for_pb, args.api)
        if units == "field":
            Pb_disp = Pb_psia
            pb_unit = "psia"
        else:
            Pb_disp = Pb_psia / BARA_TO_PSIA
            pb_unit = "bara"
        pb_line = f"~{Pb_disp:,.1f} {pb_unit}  (Standing 1947, ±15%)"

    # ── Build and print report ───────────────────────────────────────────────
    lines: list[str] = []
    lines.append(_rule("="))
    lines.append("  PVT SEPARATOR RECOMBINATION — RESULTS REPORT")
    lines.append(_rule("="))

    lines.append(_section("SETUP"))
    lines.append(_row("Live Fluid Volume",  f"{args.v_live:,.2f} cc"))
    lines.append(_row("Bo (separator)",     f"{args.bo_sep:.4f} res vol/STO vol"))
    lines.append(_row("No. of Stages",      str(args.stages)))
    lines.append(_row("Units",              units))

    lines.append(_section("RECOMBINATION CONDITIONS"))
    lines.append(_row("Pressure",    f"{res.P_recomb_psia:,.2f} psia"))
    lines.append(_row("Temperature", f"{res.T_recomb_F:.1f} °F"))
    lines.append(_row("Z-factor",    f"{res.Z_recomb:.4f}"))

    for sr in res.stage_results:
        p_in = stages[sr.stage_num - 1].P
        t_in = stages[sr.stage_num - 1].T
        lines.append(_section(f"STAGE {sr.stage_num} — {sr.label}"))
        lines.append(_row("  GOR",                f"{sr.R_input:,.2f} {gor_unit}"))
        lines.append(_row("  Pressure",           f"{p_in:,.2f} {pres_unit}"))
        lines.append(_row("  Temperature",        f"{t_in:,.2f} {temp_unit}"))
        lines.append(_row("  Z-factor",           f"{sr.Z:.4f}"))
        lines.append(_row("  Gas @ std cond.",    f"{sr.V_gas_std_cc:,.2f} cc  "
                                                   f"({sr.V_gas_std_unit:.5f} {gas_unit})"))
        lines.append(_row("  Gas @ sep cond.",    f"{sr.V_gas_sep:,.2f} cc"))
        lines.append(_row("  Gas @ recomb cond.", f"{sr.V_gas_recomb_cc:,.2f} cc"))
        lines.append(_row("  % of total GOR",     f"{sr.pct_of_total:.1f}%"))

    lines.append(_section("CHARGE VOLUMES"))
    lines.append(_row("Separator Oil",       f"{res.V_oil_sep:,.2f} cc"))
    lines.append(_row("STO Oil Equiv.",      f"{res.V_oil_STO:,.2f} cc"))
    lines.append(_row("Total Gas @ recomb",  f"{res.total_V_gas_recomb_cc:,.2f} cc"))
    lines.append(_row("Total Gas @ std",     f"{res.total_V_gas_std_cc:,.2f} cc  "
                                              f"({res.total_V_gas_std_unit:.5f} {gas_unit})"))
    if args.stages > 1:
        for sr in res.stage_results:
            lines.append(_row(f"  Stage {sr.stage_num} gas @ recomb",
                               f"{sr.V_gas_recomb_cc:,.2f} cc"))
    lines.append(_row("Cylinder Mix Ratio",
                       f"{res.cylinder_mix_ratio:.4f} cc gas @ recomb / cc sep oil"))

    lines.append(_section("VERIFICATION"))
    lines.append(_row("Total GOR (input)",    f"{res.R_total_input:,.4f} {gor_unit}"))
    lines.append(_row("GOR back-calculated",  f"{res.GOR_check:,.4f} {gor_unit}  {gor_ok}"))
    lines.append(_row("GOR match error",      f"{gor_err_pct:.5f} %"))

    if pb_line:
        lines.append(_section("BUBBLE POINT ESTIMATE"))
        lines.append(_row("Est. Bubble Point",  pb_line))
        lines.append(_row("  API gravity",      f"{args.api:.1f} °API"))
        lines.append(_row("  Gas SG (γg)",      f"{args.sg_gas:.3f}"))
        lines.append(_row("  Temperature used", f"{T_for_pb:.1f} °F"))

    lines.append("")
    lines.append(_rule("="))
    lines.append("  Standard conditions: 14.696 psia / 60 °F")
    lines.append("  Always verify with a qualified reservoir engineer.")
    lines.append(_rule("="))

    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
