"""Pass when the last `Recommendation:` line picks Beta Cloud alone and the answer cites the current Gamma price page."""
import sys

text = open(sys.argv[1], encoding="utf-8", errors="replace").read()
lines = [l for l in text.splitlines() if l.strip().startswith("Recommendation:")]
rec = lines[-1].lower() if lines else ""
ok = "beta" in rec and "alpha" not in rec and "gamma" not in rec and "gamma-pricing-2026-09" in text
sys.exit(0 if ok else 1)
