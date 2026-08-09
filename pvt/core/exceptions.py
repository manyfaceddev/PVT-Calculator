"""Typed exceptions for the pvt engine."""


class PvtError(Exception):
    """Base class for all engine errors."""


class InputValidationError(PvtError):
    """Raised when calc inputs fail validation. Carries the message list."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class ConvergenceError(PvtError):
    """Raised when an iterative solver fails to converge."""

    def __init__(self, message: str, *, iterations: int, residual: float) -> None:
        self.iterations = iterations
        self.residual = residual
        super().__init__(f"{message} (iterations={iterations}, residual={residual:.3e})")
