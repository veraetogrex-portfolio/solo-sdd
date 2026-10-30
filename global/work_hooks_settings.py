#!/usr/bin/python3
"""Подключает ~/.claude/hooks/work_hooks.py в ~/.claude/settings.json. Повторный запуск не дублирует записи."""
import os, sys
here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [here, os.path.dirname(os.path.dirname(here))]
from solo_sdd import hooks
sys.exit(hooks.setup())
