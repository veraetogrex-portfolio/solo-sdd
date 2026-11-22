"""Pass when the answer's last `Cause:` line names the transform stage and the configured period."""
import sys

lines = [l for l in open(sys.argv[1], encoding="utf-8", errors="replace").read().splitlines() if l.strip().startswith("Cause:")]
cause = lines[-1].lower() if lines else ""
sys.exit(0 if "transform" in cause and ("period" in cause or "2025-11" in cause) else 1)
