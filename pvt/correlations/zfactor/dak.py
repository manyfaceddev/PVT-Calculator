"""Dranchuk & Abou-Kassem (1975) Z-factor, Newton iteration with the CORRECT derivative.

Coefficients per the original paper. The reference workbook ("Z factor calculation.xls")
uses a wrong derivative that still converges (ledger D-005); this module uses the true one.
Validity: 0.2 <= Ppr < 30 (accepting Ppr < 0.2 as the ideal-gas limit), 1.0 < Tpr <= 3.0.
"""
import math

from pvt.core.exceptions import ConvergenceError, InputValidationError

_A = (0.3265, -1.07, -0.5339, 0.01569, -0.05165, 0.5475,
      -0.7361, 0.1844, 0.1056, 0.6134, 0.721)


def z_factor(p_psia: float, t_r: float, tpc_r: float, ppc_psia: float, *,
             tol: float = 1e-10, max_iter: int = 100, z0: float | None = None) -> float:
    errors = []
    if p_psia < 0:
        errors.append(f"pressure {p_psia} psia must be >= 0")
    if t_r <= 0 or tpc_r <= 0 or ppc_psia <= 0:
        errors.append("temperature and pseudo-criticals must be positive")
    if z0 is not None and z0 <= 0:
        errors.append(f"z0 {z0} must be > 0 when given")
    if errors:
        raise InputValidationError(errors)
    tpr, ppr = t_r / tpc_r, p_psia / ppc_psia
    if not (1.0 < tpr <= 3.0) or ppr >= 30.0:
        raise InputValidationError(
            [f"(Ppr={ppr:.3f}, Tpr={tpr:.3f}) outside DAK validity (Ppr<30, 1<Tpr<=3)"])
    a1, a2, a3, a4, a5, a6, a7, a8, a9, a10, a11 = _A
    c1 = a1 + a2 / tpr + a3 / tpr**3 + a4 / tpr**4 + a5 / tpr**5
    c2 = a6 + a7 / tpr + a8 / tpr**2
    c3 = a9 * (a7 / tpr + a8 / tpr**2)
    z = z0 if z0 is not None else 1.0
    residual = math.inf
    for _ in range(max_iter):
        rho = 0.27 * ppr / (z * tpr)
        e = math.exp(-a11 * rho**2)
        c4 = a10 * (1 + a11 * rho**2) * (rho**2 / tpr**3) * e
        f = z - (1 + c1 * rho + c2 * rho**2 - c3 * rho**5 + c4)
        residual = abs(f)
        if residual <= tol:
            return z
        # dF/dZ with drho/dZ = -rho/Z:
        dc4 = (2 * a10 * rho**2 / (tpr**3 * z)) * e * (1 + a11 * rho**2 - (a11 * rho**2) ** 2)
        df = 1 + c1 * rho / z + 2 * c2 * rho**2 / z - 5 * c3 * rho**5 / z + dc4
        z -= f / df
        if z <= 0:
            z = 1e-3
    raise ConvergenceError("DAK Newton failed", iterations=max_iter, residual=residual)
