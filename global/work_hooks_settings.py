#!/usr/bin/python3
"""Connects ~/.claude/hooks/work_hooks.py in ~/.claude/settings.json. A repeated run does not duplicate entries."""
import os, sys
here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [here, os.path.dirname(os.path.dirname(here))]
from solo_sdd import hooks
sys.exit(hooks.setup())
