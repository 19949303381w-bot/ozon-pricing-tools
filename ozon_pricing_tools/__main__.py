"""Command-line interface. Does not access files, accounts or the network."""
import argparse
import json

from .calculator import CalculationError, MissingValueError, calculate


def main(argv=None):
    parser = argparse.ArgumentParser(description='Offline Ozon pricing estimate using your own costs and rates.')
    parser.add_argument('--mode', choices=('forward', 'reverse'), default='forward')
    parser.add_argument('--cost', help='Purchase cost in CNY')
    parser.add_argument('--exchange', help='RUB per 1 CNY; enter your verified exchange rate')
    parser.add_argument('--sale-rub', help='RUB selling price for forward mode')
    parser.add_argument('--margin', help='Target sales margin in percent for reverse mode')
    for field in ('domestic', 'cross-border', 'packing', 'fulfilment'):
        parser.add_argument('--' + field, help='Per-item fixed cost in CNY; omitted means 0')
    for field in ('commission', 'advertising', 'payment'):
        parser.add_argument('--' + field, help='Percent of selling revenue; omitted means 0')
    inputs = vars(parser.parse_args(argv))
    try:
        output = calculate(**inputs).to_dict()
    except CalculationError as error:
        output = {'status': 'empty' if isinstance(error, MissingValueError) else 'error', 'message': str(error)}
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 2
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
