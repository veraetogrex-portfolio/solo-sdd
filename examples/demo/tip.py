#!/usr/bin/env python3
"""Tip and total of a restaurant bill: python3 tip.py <bill> <percent>."""
import argparse
import sys
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENT = Decimal("0.01")


def amount(text):
    """A non-negative decimal number, else argparse refuses it with exit code 2."""
    try:
        value = Decimal(text)
    except InvalidOperation:
        value = None
    if value is None or not value.is_finite() or value < 0:
        raise argparse.ArgumentTypeError("must be a non-negative number: %r" % text)
    return value


def tip(bill, percent):
    """(tip, total): the tip rounded half up to cents, the total is the bill plus that tip."""
    t = (bill * percent / 100).quantize(CENT, rounding=ROUND_HALF_UP)
    return t, (bill + t).quantize(CENT, rounding=ROUND_HALF_UP)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tip.py", description="Tip and total of a bill.")
    parser.add_argument("bill", type=amount, help="the bill, for example 40 or 10.10")
    parser.add_argument("percent", type=amount, help="the tip percent, for example 15")
    args = parser.parse_args(argv)
    t, total = tip(args.bill, args.percent)
    print("tip %s, total %s" % (t, total))
    return 0


if __name__ == "__main__":
    sys.exit(main())
