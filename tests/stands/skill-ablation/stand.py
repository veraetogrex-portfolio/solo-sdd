#!/usr/bin/env python3
"""Live Scenario steps 1-5 of skill-ablation without model calls: the real runner `tests/stands/skill-ablation.py`
on the committed task sets, each task's `reference.jsonl` standing in for the transcript of every prompt.

Usage: python3 tests/stands/skill-ablation/stand.py
Code 0 means every check matched. The stand creates and removes its temporary folder itself."""
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "tests/stands/skill-ablation.py"
SETS = ROOT / "tests/stands/skill-ablation"
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("ok: " if ok else "FAIL: ") + name + ("" if ok else " — " + str(detail)[-600:]))


def run(*args):
    p = subprocess.run([sys.executable, str(RUNNER)] + [str(a) for a in args], cwd=ROOT, capture_output=True,
                       text=True, stdin=subprocess.DEVNULL, timeout=300)
    return p.returncode, p.stdout + p.stderr


def full_run(tmp, skill):
    out = tmp / skill
    code, text = run("prepare", skill, "--budget", 6, "--out", out)
    prompts = sorted(out.glob("*.prompt.md"))
    check("prepare %s --budget 6: 6 prompts, exit 0" % skill, code == 0 and len(prompts) == 6, text)
    for p in prompts:
        pid = p.name[:-len(".prompt.md")]
        task = pid.rsplit("-", 1)[0]
        shutil.copyfile(SETS / skill / task / "reference.jsonl", out / (pid + ".jsonl"))
    code, text = run("grade", out)
    rows = [l for l in text.splitlines() if l.startswith("| ") and not l.startswith("| task")]
    check("grade %s: 6 rows, all pass" % skill, code == 0 and len(rows) == 6 and all("| pass |" in r for r in rows), text)
    check("grade %s: compare full 2 of 2, cut 2 of 2, none 2 of 2" % skill,
          "compare: full 2 of 2, cut 2 of 2, none 2 of 2" in text, text)


def work_folders(run):
    try:
        return [Path(p["work"]) for p in json.loads((run / "manifest.json").read_text())["prompts"]]
    except (OSError, ValueError, KeyError):
        return []


def main():
    code, text = run("audit")
    check("audit: docs/skills-audit.md matches every skill of targets.json", code == 0, text)
    tmp = Path(tempfile.mkdtemp(prefix="skill-ablation-stand-"))
    try:
        full_run(tmp, "debug-profile")
        full_run(tmp, "evidence-research")
        code, text = run("prepare", "evidence-research", "--budget", 4, "--out", tmp / "short")
        check("prepare evidence-research --budget 4: 4 prompts, the budget line, exit 3",
              code == 3 and "budget reached: 2 of 6 calls not made" in text
              and len(list((tmp / "short").glob("*.prompt.md"))) == 4, text)
        code, text = run("grade", tmp / "short")
        check("grade without transcripts: 4 rows not run, 2 calls not made",
              "not run: 4; leaked: 0; unreadable: 0; not made: 2" in text, text)
    finally:
        spec = importlib.util.spec_from_file_location("skill_ablation", RUNNER)
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        works = [p for folder in tmp.iterdir() for p in work_folders(folder)]
        for folder in tmp.iterdir():
            runner.remove(folder)
        shutil.rmtree(tmp, ignore_errors=True)
    check("temporary folders removed (the runs and their %d work folders)" % len(works),
          not tmp.exists() and len(works) == 16 and not any(p.exists() for p in works))
    print("skill-ablation stand: %d of %d checks passed" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
