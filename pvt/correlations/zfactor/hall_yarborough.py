"""Hall & Yarborough (1973) Z-factor, Newton iteration on reduced gas density.

Canonical form (Hall & Yarborough, 1973): with the RECIPROCAL reduced
temperature t = Tpc/T (note: reciprocal of the usual Tpr = T/Tpc) and

    A = 0.06125 * t * Ppr * exp(-1.2*(1-t)**2)

Z = A/y, where the reduced density y solves

    F(y) = -A + (y+y^2+y^3-y^4)/(1-y)^3 - B*y^2 + C*y^D = 0

    B = t*(14.76 - 9.76*t + 4.58*t**2)
    C = t*(90.7 - 242.2*t + 42.4*t**2)
    D = 2.18 + 2.82*t

solved by Newton's method with

    F'(y) = (1+4y+4y^2-4y^3+y^4)/(1-y)^4 - 2*B*y + C*D*y^(D-1)

(the closed form of d/dy[(y+y^2+y^3-y^4)/(1-y)^3 - B*y^2 + C*y^D],
symbolically verified). This F' agrees with the Gas_Gradient VBA
`CalculateZFactor` kernel (docs/reference/gasprop_functions.bas): that
routine solves the algebraically equivalent residual F(y)/y = 0 (dividing
through by y > 0 does not move the root), for which its stated derivative
reduces to exactly the same building blocks used here.

D-006: a different workbook's CVD "Additional_QC" sheet implements a
broken variant of this equation (uses the ordinary reduced temperature Tr
instead of t, omits the ·t factor in the A-term, and returns the reduced
density y itself as "Z"). This module implements the canonical Hall &
Yarborough (1973) equation per the Gas_Gradient VBA reference, not that
broken variant. See docs/excel-deviations.md D-006.
"""
import math

from pvt.core.exceptions import ConvergenceError, InputValidationError

_Y0 = 1e-3
_Y_MIN = 1e-6
_Y_MAX = 0.999


def z_factor(p_psia: float, t_r: float, tpc_r: float, ppc_psia: float, *,
             tol: float = 1e-10, max_iter: int = 60) -> float:
    errors = []
    if p_psia < 0:
        errors.append(f"pressure {p_psia} psia must be >= 0")
    if t_r <= 0 or tpc_r <= 0 or ppc_psia <= 0:
        errors.append("temperature and pseudo-criticals must be positive")
    if errors:
        raise InputValidationError(errors)

    t = tpc_r / t_r
    ppr = p_psia / ppc_psia
    a = 0.06125 * t * ppr * math.exp(-1.2 * (1.0 - t) ** 2)
    b = t * (14.76 - 9.76 * t + 4.58 * t * t)
    c = t * (90.7 - 242.2 * t + 42.4 * t * t)
    d = 2.18 + 2.82 * t

    y = _Y0
    residual = math.inf
    for _ in range(max_iter):
        if y >= 1.0:
            y = _Y_MAX
        f = -a + (y + y**2 + y**3 - y**4) / (1.0 - y) ** 3 - b * y**2 + c * y**d
        residual = abs(f)
        if residual <= tol:
            return a / y
        fprime = (
            (1.0 + 4.0 * y + 4.0 * y**2 - 4.0 * y**3 + y**4) / (1.0 - y) ** 4
            - 2.0 * b * y
            + c * d * y ** (d - 1.0)
        )
        y -= f / fprime
        if y <= 0.0:
            y = _Y_MIN
    raise ConvergenceError("Hall-Yarborough Newton failed", iterations=max_iter,
                            residual=residual)
