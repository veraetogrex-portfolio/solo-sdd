"""Data root: solo_sdd/data in the wheel, else the clone root (the package parent)."""
import os

_PACKAGE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_PACKAGE, "data")
ROOT = _DATA if os.path.isdir(_DATA) else os.path.dirname(_PACKAGE)
