#!/usr/bin/env python3
"""Живой сценарий pr-wait-required без репозитория (Fallback): настоящий global/sdd_pr.py wait
против подмены gh первой в PATH. Подмена отдаёт правила ветки с обязательной `PR title` и список
проверок; срок застрявшей проверки 300 с подменён параметром --stuck 1.

Использование: python3 tests/stands/required-checks.py
Код 0 — все сценарии сошлись. Временную папку стенд создаёт и удаляет сам."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "global/sdd_pr.py"
URL = "https://github.com/o/stand/pull/1"
RULES = [{"type": "required_status_checks", "parameters": {
    "required_status_checks": [{"context": "PR title"}]}}]
CHECKS = {"name": "Checks", "state": "SUCCESS", "bucket": "pass", "link": ""}
CODEQL = {"name": "CodeQL", "state": "SUCCESS", "bucket": "pass", "link": ""}
TITLE_QUEUED = {"name": "PR title", "state": "QUEUED", "bucket": "pending", "link": ""}
TITLE_PASS = {"name": "PR title", "state": "SUCCESS", "bucket": "pass", "link": ""}
WARN = "предупреждение: правила ветки не прочитались, обязательные проверки не сверены"

GH = f"""#!{sys.executable}
import json, os, sys
cfg = json.load(open(os.environ["STAND_CFG"]))
a = sys.argv[1:]
if a[:2] == ["pr", "view"]:
    print(json.dumps({{"baseRefName": "main"}}))
elif a[:2] == ["pr", "checks"]:
    print(json.dumps(cfg["checks"]))
elif a[:1] == ["api"]:
    key = "rules" if "/rules/" in a[1] else "branch"
    if cfg.get(key) == "fail":
        sys.stderr.write("gh: Forbidden (HTTP 403)\\n")
        sys.exit(1)
    print(json.dumps(cfg.get(key, [] if key == "rules" else {{}})))
else:
    sys.exit(1)
"""

# имя, настройка подмены, ожидаемые (код, stdout, stderr)
CASES = [
    ("обязательная висит в очереди", {"rules": RULES, "checks": [CHECKS, CODEQL, TITLE_QUEUED]},
     (4, f"PR #1 {URL} CI: infra\nне стартовала обязательная проверка PR title", "")),
    ("обязательной нет в списке", {"rules": RULES, "checks": [CHECKS, CODEQL]},
     (4, f"PR #1 {URL} CI: infra\nне стартовала обязательная проверка PR title", "")),
    ("обязательная прошла", {"rules": RULES, "checks": [CHECKS, TITLE_PASS]},
     (0, f"PR #1 {URL} CI: green", "")),
    ("обязательных нет", {"checks": [CHECKS, CODEQL]},
     (0, f"PR #1 {URL} CI: green", "")),
    ("правила не читаются", {"rules": "fail", "checks": [CHECKS, CODEQL]},
     (0, f"PR #1 {URL} CI: green", WARN)),
]


def main():
    d = Path(tempfile.mkdtemp(prefix="stand-required-"))
    try:
        (d / "gh").write_text(GH)
        (d / "gh").chmod(0o755)
        env = dict(os.environ, PATH=f"{d}:{os.environ['PATH']}", STAND_CFG=str(d / "cfg.json"))
        ok = 0
        for name, cfg, want in CASES:
            (d / "cfg.json").write_text(json.dumps(cfg))
            t = time.monotonic()
            p = subprocess.run([sys.executable, str(SCRIPT), "wait", URL, "--timeout", "30",
                                "--interval", "0.2", "--stuck", "1"],
                               capture_output=True, text=True, stdin=subprocess.DEVNULL, env=env, timeout=60)
            got = (p.returncode, p.stdout.strip(), p.stderr.strip())
            good = got == want
            ok += good
            print(f"{'ok  ' if good else 'FAIL'} {name}: код {p.returncode}, {time.monotonic() - t:.1f} с, "
                  f"{p.stdout.strip().replace(chr(10), ' | ')}" + (f" | stderr: {got[2]}" if got[2] else ""))
            if not good:
                print(f"     ждали: {want}")
        print(f"итог: {ok} из {len(CASES)}")
        return 0 if ok == len(CASES) else 1
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
