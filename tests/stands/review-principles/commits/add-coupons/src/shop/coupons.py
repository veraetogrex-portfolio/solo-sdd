"""Coupons."""
import datetime


def apply_coupon(total, coupon, today=None):
    """The total after the coupon."""
    today = today or datetime.date.today()
    if coupon["expires"] < today:
        return total
    return total * (1 - coupon["percent"] / 100.0)
