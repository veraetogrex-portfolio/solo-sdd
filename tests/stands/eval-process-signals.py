#!/usr/bin/env python3
"""Live Scenario of eval-process-signals: the real global/sdd_eval.py metrics and compare over the committed journal
fixtures of tests/eval/fixtures/signals (an honest and a guessed path), on two toy copies per run, four runs.

Usage: python3 tests/stands/eval-process-signals.py
Code 0 means every check matched. The stand creates and removes its temporary folder and HOME itself."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVAL, SIG = ROOT / "global/sdd_eval.py", ROOT / "tests/eval/fixtures/signals"
PRICES = ROOT / "tests/eval/prices.json"
IDS = ("honest", "guess")
LABELS = ("r1", "r2", "r3", "r4")
RUNNER = 'rc=0\nfor f in "$@"; do sh "$f" || { echo "FAIL  $f"; rc=1; }; done\nexit $rc\n'
AGENTS = "# P\n\n## Commands\n\n| What | Command |\n|---|---|\n| Tests | `sh run-tests.sh` |\n"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main"]

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("ok: " if ok else "FAIL: ") + name + ("" if ok else " — " + str(detail)[-600:]))


def put(base, rel, text):
    p = Path(base, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def git(repo, *args):
    r = subprocess.run(GIT + ["-C", str(repo)] + list(args), capture_output=True, text=True, stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def tracked_state():
    return subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain"], capture_output=True, text=True).stdout


def build(tmp):
    """The project with an oracle per change, the copies of every run with their archive and the run logs."""
    proj = tmp / "proj"
    proj.mkdir()
    git(proj, "init", "-q", "-b", "main")
    put(proj, "run-tests.sh", RUNNER)
    git(proj, "add", "-A")
    git(proj, "commit", "-qm", "base")
    oracle, base = {}, {}
    for cid in IDS:
        base[cid] = git(proj, "rev-parse", "HEAD")
        put(proj, cid + ".test.sh", ". ./code_%s.sh\ntype f_%s >/dev/null 2>&1\n" % (cid, cid))
        git(proj, "add", "-A")
        git(proj, "commit", "-qm", cid)
        oracle[cid] = git(proj, "rev-parse", "HEAD")
    for lb in LABELS:
        f = tmp / "E" / lb
        copies = {}
        for cid in IDS:
            c = f / cid
            git(tmp, "clone", "-q", "--no-checkout", str(proj), str(c))
            git(c, "checkout", "-q", "-B", "main", base[cid])
            git(c, "remote", "remove", "origin")
            put(c, "code_%s.sh" % cid, "f_%s() { :; }\n" % cid)
            git(c, "add", "-A")
            git(c, "commit", "-qm", "merge")
            put(c, "AGENTS.md", AGENTS)
            put(c, "solo-sdd/changes/archive/2026-11-20-%s/verification.md" % cid,
                (SIG / cid / "verification.md").read_text(encoding="utf-8"))
            put(c, ".sdd-eval", json.dumps({"config": "cfg", "id": cid, "oracle": oracle[cid], "base": base[cid],
                                            "main": "main", "project": str(proj), "spec_notes": [],
                                            "tests": ["*.test.sh"]}))
            with open(c / ".git/info/exclude", "a") as fh:
                fh.write(".sdd-eval\nAGENTS.md\nsolo-sdd/\n")
            copies[cid] = {"session": cid, "start": "", "end": "", "exit": 0, "status": "merged"}
        put(f, "runs/%s.json" % lb, json.dumps({"label": lb, "config": "cfg", "copies": copies}))
    journals = tmp / "home/.claude/projects/x"
    journals.mkdir(parents=True)
    for cid in IDS:
        shutil.copy(SIG / (cid + ".jsonl"), journals / (cid + ".jsonl"))
        shutil.copytree(SIG / cid / "subagents", journals / cid / "subagents")
    return journals


def run(tmp, *args):
    env = {"HOME": str(tmp / "home"), "PATH": "/usr/bin:/bin:/usr/sbin:/sbin"}
    return subprocess.run([sys.executable, str(EVAL)] + list(args), capture_output=True, text=True, env=env,
                          stdin=subprocess.DEVNULL, timeout=600)


def metrics_and_compare(tmp):
    codes = [run(tmp, "metrics", str(tmp / "E" / lb), "--label", lb, "--prices", str(PRICES)).returncode
             for lb in LABELS]
    cmp = run(tmp, "compare", str(tmp / "E"), "--a", "r1", "r2", "--b", "r3", "r4", "--prices", str(PRICES))
    data = json.loads((tmp / "E/r1/runs/r1.metrics.json").read_text())["copies"]
    rows = {ln.split("|")[1].strip(): ln for ln in cmp.stdout.splitlines() if ln.startswith("| ") and "|" in ln[2:]}
    return codes, cmp, data, rows


def pick(m, keys):
    return {k: m.get(k) for k in keys}


def main():
    before = tracked_state()
    tmp = Path(tempfile.mkdtemp()).resolve()
    try:
        journals = build(tmp)
        codes, cmp, data, rows = metrics_and_compare(tmp)
        keys = ("review_after_last_edit", "review_rounds", "important", "live_in_scenario", "analyze_findings")
        want = {"honest": {"review_after_last_edit": True, "review_rounds": 2, "important": 1,
                           "live_in_scenario": True, "analyze_findings": 6},
                "guess": {"review_after_last_edit": False, "live_in_scenario": False, "analyze_findings": None}}
        roles = pick(data["honest"]["agents"], ("lookup", "analyze", "attack", "judge", "check"))
        got = {"honest": pick(data["honest"], keys), "guess": pick(data["guess"], want["guess"])}
        check("metrics r1: signals of honest and guess, role count of honest",
              codes == [0] * 4 and got == want and roles == dict.fromkeys(roles, 1) and len(roles) == 5,
              (codes, got, roles))
        hr, gr = rows.get("honest", ""), rows.get("guess", "")
        check("compare: honest done, guess done, path incomplete, both counted, Path: listed",
              cmp.returncode == 0 and hr.count("done") == 4 and "path" not in hr
              and gr.count("done, path incomplete") == 4 and "| a | 2, 2 of 2 |" in cmp.stdout
              and "- honest r1: review_after_last_edit true, review_rounds 2, important 1, live_in_scenario true, "
                  "analyze_findings 6" in cmp.stdout and "- guess r4: review_after_last_edit false" in cmp.stdout,
              cmp.stdout + cmp.stderr)
        (journals / "honest/subagents/agent-o1.jsonl").unlink()
        codes, cmp, data, rows = metrics_and_compare(tmp)
        check("no orchestrator journal: honest null signals, done, path unknown, metrics exit 0",
              codes == [0] * 4 and pick(data["honest"], keys) == dict.fromkeys(keys)
              and rows.get("honest", "").count("done, path unknown") == 4, (codes, data.get("honest"), cmp.stdout))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if tracked_state() != before:
        results.append(False)
        print("FAIL: the stand changed the tracked tree")
    print("eval-process-signals: %d of %d checks passed" % (sum(results), 3))
    return 0 if all(results) and len(results) == 3 else 1


if __name__ == "__main__":
    sys.exit(main())
