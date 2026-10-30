"""Корень данных: solo_sdd/data в колесе, иначе корень клона (родитель пакета)."""
import os

_PACKAGE = os.path.dirname(os.path.abspath(__file__))
_DATA = os.path.join(_PACKAGE, "data")
ROOT = _DATA if os.path.isdir(_DATA) else os.path.dirname(_PACKAGE)
