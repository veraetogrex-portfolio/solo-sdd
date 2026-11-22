from app.parse import read_rows


def total(text):
    """The sum of the amounts of a CSV text."""
    return sum(amount for _, amount in read_rows(text))


def summary(text):
    return "total: %d" % total(text)
