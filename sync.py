"""Обёртка над solo_sdd.layout: python3 sync.py status|push|pull."""
import os, sys

here = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [here, os.path.dirname(os.path.dirname(here))]
from solo_sdd import layout

if __name__ == "__main__":
    sys.exit(layout.main(sys.argv[1:]))
