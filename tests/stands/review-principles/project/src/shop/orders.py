"""Orders."""


def place(cart, user):
    """A new order of the cart for the user."""
    return {"user": user, "items": list(cart), "paid": 0}
