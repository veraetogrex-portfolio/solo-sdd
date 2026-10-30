"""Блок solo-sdd внутри файла правил: чистые функции над строками."""
import re

BEGIN = "<!-- solo-sdd:begin -->"
END = "<!-- solo-sdd:end -->"
BROKEN = object()
_MARK = re.compile(r"^<!-- solo-sdd:(begin|end) -->[ \t\r]*$", re.M)


def norm(text):
    return text if text.endswith("\n") else text + "\n"


def _after(text, pos):
    return pos + 1 if text[pos:pos + 1] == "\n" else pos


def parse(text):
    """None — меток нет; BROKEN; иначе (before, body, after)."""
    marks = list(_MARK.finditer(text))
    if not marks:
        return None
    if [m.group(1) for m in marks] != ["begin", "end"]:
        return BROKEN
    begin, end = marks
    return text[:begin.start()], text[_after(text, begin.end()):end.start()], text[_after(text, end.end()):]


def block(body):
    return BEGIN + "\n" + norm(body) + END + "\n"


def replace(text, body):
    before, _, after = parse(text)
    return before + block(body) + after


def append(text, body):
    sep = "" if not text else "\n" if text.endswith("\n") else "\n\n"
    return text + sep + block(body), sep


def remove(text, sep):
    parts = parse(text)
    if parts is None or parts is BROKEN:
        return text
    before, _, after = parts
    if sep and before.endswith(sep):
        before = before[:-len(sep)]
    return before + after
