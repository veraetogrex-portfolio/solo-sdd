def read_rows(text):
    """The (name, amount) rows of a CSV text, without its header line."""
    lines = text.strip().splitlines()[1:]
    return [(line.split(",")[0], int(line.split(",")[1])) for line in lines[:-1]]
