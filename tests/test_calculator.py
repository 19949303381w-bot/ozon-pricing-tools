import contextlib
from decimal import Decimal
import io
import json
import unittest

from ozon_pricing_tools import CalculationError, MissingValueError, calculate
from ozon_pricing_tools.__main__ import main


class PricingTests(unittest.TestCase):
    def test_forward_full_example(self):
        result = calculate(cost='25', exchange='12', sale_rub='1200', domestic='3',
                           cross_border='15', packing='1', fulfilment='2',
                           commission='15', advertising='5', payment='1')
        self.assertEqual(result.fixed_cost_cny, Decimal('46'))
        self.assertEqual(result.selling_cny, Decimal('100'))
        self.assertEqual(result.profit_cny, Decimal('33'))
        self.assertEqual(result.profit_rub, Decimal('396'))
        self.assertEqual(result.margin_percent, Decimal('33'))
        self.assertEqual(result.commission_cny, Decimal('15'))
        self.assertEqual(result.advertising_cny, Decimal('5'))
        self.assertEqual(result.payment_cny, Decimal('1'))
        self.assertEqual(result.to_dict()['break_even_rub'], '698.73')

    def test_reverse_roundtrip_uses_margin_on_revenue(self):
        reverse = calculate(mode='reverse', cost='46', exchange='12', margin='30',
                            commission='15', advertising='5', payment='1')
        self.assertEqual(reverse.to_dict()['selling_rub'], '1126.53')
        self.assertAlmostEqual(reverse.margin_percent, Decimal('30'), places=40)
        forward = calculate(cost='46', exchange='12', sale_rub=reverse.selling_rub,
                            commission='15', advertising='5', payment='1')
        self.assertAlmostEqual(forward.margin_percent, Decimal('30'), places=40)
        self.assertAlmostEqual(forward.profit_cny, reverse.profit_cny, places=40)

    def test_decimal_tenths_and_display_do_not_reprice(self):
        result = calculate(cost='0.1', domestic='0.2', exchange='1', sale_rub='1')
        self.assertEqual(result.fixed_cost_cny, Decimal('0.3'))
        self.assertEqual(result.profit_cny, Decimal('0.7'))
        reverse = calculate(mode='reverse', cost='1', exchange='1', margin='40')
        self.assertEqual(reverse.to_dict()['selling_cny'], '1.67')
        self.assertNotEqual(reverse.selling_cny, Decimal('1.67'))

    def test_zero_is_real_and_zero_revenue_margin_is_undefined(self):
        zero = calculate(cost='0', exchange='1', sale_rub='0', commission='0')
        self.assertEqual(zero.to_dict()['profit_cny'], '0.00')
        self.assertEqual(zero.to_dict()['break_even_rub'], '0.00')
        self.assertIsNone(zero.margin_percent)
        loss = calculate(cost='4', exchange='2', sale_rub='0')
        self.assertEqual(loss.profit_cny, Decimal('-4'))
        self.assertIsNone(loss.margin_percent)
        self.assertEqual(loss.to_dict()['profit_rub'], '-8.00')

    def test_missing_required_inputs_differ_from_zero(self):
        for inputs in ({'exchange': '1', 'sale_rub': '1'},
                       {'cost': '1', 'exchange': '', 'sale_rub': '1'},
                       {'cost': '1', 'exchange': '1'},
                       {'mode': 'reverse', 'cost': '1', 'exchange': '1', 'margin': ' '}):
            with self.subTest(inputs=inputs), self.assertRaises(MissingValueError):
                calculate(**inputs)
        self.assertEqual(calculate(cost='1', exchange='1', sale_rub='2', domestic='').profit_cny,
                         Decimal('1'))

    def test_forward_loss_and_fees_at_or_above_100_percent(self):
        for rate in ('100', '150'):
            result = calculate(cost='1', exchange='1', sale_rub='10',
                               commission='100', advertising=str(int(rate) - 100))
            self.assertLess(result.profit_cny, Decimal('0'))
            self.assertIsNone(result.break_even_rub)

    def test_reverse_rejects_unreachable_margin_even_at_zero_cost(self):
        for cost in ('0', '10'):
            for margin in ('80', '90'):
                with self.subTest(cost=cost, margin=margin), self.assertRaises(CalculationError):
                    calculate(mode='reverse', cost=cost, exchange='1', margin=margin, commission='20')

    def test_invalid_and_nonfinite_values_are_not_coerced(self):
        for key, value in (('cost', '-1'), ('cost', True), ('cost', 'NaN'), ('cost', 'Infinity'),
                           ('cost', []), ('exchange', '0'), ('exchange', '-2'), ('commission', '100.1'),
                           ('cost', '1000000.01'), ('sale_rub', '1000000000.01')):
            inputs = {'cost': '1', 'exchange': '1', 'sale_rub': '10', key: value}
            with self.subTest(key=key, value=value), self.assertRaises(CalculationError):
                calculate(**inputs)
        with self.assertRaises(CalculationError):
            calculate(mode='other')

    def test_boundaries_and_excessive_derived_results(self):
        result = calculate(cost='1000000', exchange='1000000', sale_rub='1000000000')
        self.assertEqual(result.selling_cny, Decimal('1000'))
        with self.assertRaises(CalculationError):
            calculate(cost='1', exchange='0.000000001', sale_rub='1000000000')
        with self.assertRaises(CalculationError):
            calculate(mode='reverse', cost='1000000', exchange='1000000', margin='99')

    def test_only_active_mode_fields_are_required(self):
        self.assertEqual(calculate(cost='1', exchange='1', sale_rub='2', margin='invalid').selling_cny,
                         Decimal('2'))

    def test_extreme_decimal_exponents_fail_cleanly_or_display_a_real_loss(self):
        with self.assertRaises(CalculationError):
            calculate(cost='1', exchange='1e-1000000', sale_rub='1')
        result = calculate(cost='1', exchange='1', sale_rub='1e-100')
        self.assertLess(result.profit_cny, 0)
        self.assertIn('E+', result.to_dict()['margin_percent'])
        self.assertEqual(calculate(mode='reverse', cost='1', exchange='1', margin='50', sale_rub='invalid').selling_cny,
                         Decimal('2'))

    def test_cli_returns_parseable_result_and_truthful_error_status(self):
        for arguments, status, exit_code in ((['--cost', '1', '--exchange', '1', '--sale-rub', '2'], 'ready', 0),
                                             ([], 'empty', 2),
                                             (['--cost', '-1', '--exchange', '1', '--sale-rub', '2'], 'error', 2)):
            with self.subTest(arguments=arguments), contextlib.redirect_stdout(io.StringIO()) as output:
                code = main(arguments)
                parsed = json.loads(output.getvalue())
                self.assertEqual(code, exit_code)
                self.assertEqual(parsed['status'], status)


if __name__ == '__main__':
    unittest.main()
