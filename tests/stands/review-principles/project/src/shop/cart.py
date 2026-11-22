"""The cart."""


def total(items):
    """The cart total in cents."""
    return sum(i["price"] * i["qty"] for i in items)
