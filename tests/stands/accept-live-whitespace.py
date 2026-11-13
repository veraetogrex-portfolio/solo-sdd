#!/usr/bin/env python3
"""Stand of change accept-live-whitespace-fix: sdd_dispatch.py accept on a LIVE output aligned with two spaces.
A temporary git folder gets two status blocks: the stated text with one space (must match) and a changed word
(must mismatch and show the raw output). Nothing outside the temporary folder changes."""
import pathlib
import subprocess
import sys
import tempfile

TOOL = pathlib.Path(__file__).resolve().parents[2] / "global/sdd_dispatch.py"


def accept(root, stated):
    st = root / "st.txt"
    (root / "arch").mkdir(exist_ok=True)
    (root / "arch" / "verification.md").write_text("## Live Scenario\n\n1. `printf 'Tests  19 passed\\n'`\n", encoding="utf-8")
    st.write_text("STATUS: archived\nCHANGE: x\nWORKTREE: %s\nVALIDATE: true -> exit 0\nARCHIVE: arch\n"
                  "LIVE: printf 'Tests  19 passed\\n' -> %s\n" % (root, stated), encoding="utf-8")
    r = subprocess.run([sys.executable, str(TOOL), "accept", str(st)], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=60)
    return r.returncode, r.stdout


with tempfile.TemporaryDirectory(prefix="accept-ws-") as d:
    root = pathlib.Path(d)
    subprocess.run(["git", "init", "-q", str(root)], check=True, stdin=subprocess.DEVNULL)
    ok = accept(root, "Tests 19 passed")
    bad = accept(root, "Tests 18 passed")
checks = [("same words, extra spaces: exit 0, status matches", ok[0] == 0 and ok[1].strip() == "status matches"),
          ("changed word: exit 1, text missing", bad[0] == 1 and "text missing" in bad[1]),
          ("changed word: raw output shown", "    Tests  19 passed" in bad[1])]
for name, good in checks:
    print(("ok   " if good else "FAIL ") + name)
fails = sum(not g for _, g in checks)
print("accept-live-whitespace: %d of %d checks passed" % (len(checks) - fails, len(checks)))
sys.exit(1 if fails else 0)
