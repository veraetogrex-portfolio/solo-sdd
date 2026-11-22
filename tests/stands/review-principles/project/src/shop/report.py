"""Sales report."""


def write(path, orders):
    """Write one line per order."""
    with open(path, "w", encoding="utf-8") as out:
        for o in orders:
            out.write("%s %d\n" % (o["user"], o["paid"]))
