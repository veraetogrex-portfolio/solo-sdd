"""Pass when the verdict is `not maintained` and the answer names the archive date from the tracker."""
import sys

text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
lines = [l.strip().lower() for l in text.splitlines() if l.strip().lower().startswith("verdict:")]
sys.exit(0 if lines and lines[0] == "verdict: not maintained" and "2025-06-02" in text else 1)
