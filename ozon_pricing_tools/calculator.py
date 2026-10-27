"""General single-item pricing arithmetic; no marketplace rates or API calls."""
from dataclasses import dataclass
from decimal import Decimal, DecimalException, InvalidOperation, ROUND_HALF_UP, localcontext
from functools import wraps
from typing import Any, Optional

ZERO = Decimal('0')
ONE = Decimal('1')
HUNDRED = Decimal('100')
INPUT_LIMIT = Decimal('1000000')
SALE_LIMIT = Decimal('1000000000')
RESULT_LIMIT = Decimal('1000000000000')


class CalculationError(ValueError):
    """An invalid input or an estimate outside the supported numeric range."""


class MissingValueError(CalculationError):
    """A required field is absent, rather than explicitly zero."""


def _amount(value: Any, name: str, *, required=False, maximum=INPUT_LIMIT) -> Decimal:
    if value is None or isinstance(value, str) and not value.strip():
        if required:
            raise MissingValueError(f'{name} is required')
        return ZERO
    if isinstance(value, bool) or not isinstance(value, (str, Decimal, int, float)):
        raise CalculationError(f'{name} must be a decimal number')
    try:
        parsed = Decimal(str(value).strip())
    except (InvalidOperation, ValueError):
        raise CalculationError(f'{name} must be a decimal number') from None
    if not parsed.is_finite() or parsed < ZERO or parsed > maximum:
        raise CalculationError(f'{name} must be between 0 and {maximum}')
    return parsed


def _display(value: Optional[Decimal]) -> Optional[str]:
    if value is None:
        return None
    if abs(value) >= Decimal('1e40'):
        return format(value, '.12E')
    with localcontext() as context:
        context.prec = 50
        rounded = value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        # A genuine loss remains negative; a rounded numerical zero is "0.00".
        return format(abs(rounded) if rounded == ZERO else rounded, '.2f')


def _guard_decimal(function):
    @wraps(function)
    def guarded(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except DecimalException:
            raise CalculationError('inputs exceed the supported decimal arithmetic range') from None
    return guarded


@dataclass(frozen=True)
class Estimate:
    mode: str
    exchange: Decimal
    fixed_cost_cny: Decimal
    total_variable_rate: Decimal
    selling_cny: Decimal
    selling_rub: Decimal
    commission_cny: Decimal
    advertising_cny: Decimal
    payment_cny: Decimal
    profit_cny: Decimal
    profit_rub: Decimal
    margin_percent: Optional[Decimal]
    break_even_rub: Optional[Decimal]

    def to_dict(self):
        """Display amounts as two-decimal strings; null means undefined."""
        result = {'status': 'ready', 'mode': self.mode}
        for field in self.__dataclass_fields__:
            if field != 'mode':
                result[field] = _display(getattr(self, field))
        # Keep the exchange and proportion unrounded for machine consumers.
        result['exchange'] = str(self.exchange)
        result['total_variable_rate'] = str(self.total_variable_rate)
        return result


@_guard_decimal
def calculate(*, mode='forward', cost=None, exchange=None, sale_rub=None,
              margin=None, domestic=None, cross_border=None, packing=None,
              fulfilment=None, commission=None, advertising=None, payment=None):
    """Estimate CNY profit or reverse-price to a margin on sales revenue.

    All fixed inputs are CNY. ``exchange`` is RUB per 1 CNY. Commission,
    advertising, payment and target margin are percentages, not proportions.
    Blank optional fees mean zero; callers must enter their applicable rates.
    Decimal values are retained at 50-digit working precision until display.
    """
    if mode not in ('forward', 'reverse'):
        raise CalculationError('mode must be forward or reverse')
    with localcontext() as context:
        context.prec = 50
        purchase = _amount(cost, 'cost', required=True)
        conversion = _amount(exchange, 'exchange', required=True)
        if conversion == ZERO:
            raise CalculationError('exchange must be greater than 0')
        fixed_cost = purchase + sum((_amount(value, name) for name, value in (
            ('domestic', domestic), ('cross_border', cross_border),
            ('packing', packing), ('fulfilment', fulfilment))), ZERO)
        rates = tuple(_amount(value, name, maximum=HUNDRED) / HUNDRED for name, value in (
            ('commission', commission), ('advertising', advertising), ('payment', payment)))
        rate = sum(rates, ZERO)
        if mode == 'reverse':
            target = _amount(margin, 'margin', required=True, maximum=HUNDRED) / HUNDRED
            denominator = ONE - rate - target
            if denominator <= ZERO:
                raise CalculationError('fees plus target margin must be less than 100%')
            selling_cny = fixed_cost / denominator
        else:
            selling_cny = _amount(sale_rub, 'sale_rub', required=True, maximum=SALE_LIMIT) / conversion
        selling_rub = selling_cny * conversion
        fees = tuple(selling_cny * part for part in rates)
        profit = selling_cny - fixed_cost - sum(fees, ZERO)
        profit_rub = profit * conversion
        break_even = fixed_cost / (ONE - rate) * conversion if rate < ONE else None
        totals = (fixed_cost, selling_cny, selling_rub, sum(fees, ZERO), profit, profit_rub)
        if any(not value.is_finite() or abs(value) > RESULT_LIMIT for value in totals):
            raise CalculationError('result exceeds the supported amount range')
        if break_even is not None and (not break_even.is_finite() or break_even > RESULT_LIMIT):
            raise CalculationError('break-even price exceeds the supported amount range')
        return Estimate(mode, conversion, fixed_cost, rate, selling_cny, selling_rub,
                        *fees, profit, profit_rub,
                        profit / selling_cny * HUNDRED if selling_cny else None, break_even)
