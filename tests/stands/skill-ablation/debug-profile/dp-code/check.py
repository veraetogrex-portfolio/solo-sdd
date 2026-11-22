"""Pass when the answer's last `Cause:` line names the function where the wrong value starts, not where it shows."""
import sys

lines = [l for l in open(sys.argv[1], encoding="utf-8", errors="replace").read().splitlines() if l.strip().startswith("Cause:")]
cause = lines[-1] if lines else ""
sys.exit(0 if "parse.py" in cause and "read_rows" in cause and "report.py" not in cause else 1)
