"""Refunds."""


def refund(order, amount):
    """Refund an amount of the order."""
    order["refunded"] = order.get("refunded", 0) + amount
    return order
