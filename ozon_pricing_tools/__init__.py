"""Offline, user-supplied-rate pricing estimates with Decimal arithmetic."""
from .calculator import CalculationError, Estimate, MissingValueError, calculate

__all__ = ['CalculationError', 'Estimate', 'MissingValueError', 'calculate']
__version__ = '1.0.0'
