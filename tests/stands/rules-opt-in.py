#!/usr/bin/env python3
"""Stand of change rules-opt-in: global rules only on request, the project rules block from init.

Temporary homes and projects only; the released version is the base commit taken with git archive.
  1. a new home: install writes none of ~/AGENTS.md, ~/.codex/AGENTS.md, ~/.claude/CLAUDE.md;
  2. an old home laid out by the released version: the branch install updates the block, status ok;
     uninstall --global-rules returns the files byte for byte;
  3. a project with its own AGENTS.md: init keeps the text, appends the block, creates CLAUDE.md;
     an edit inside the block survives init --reconfigure and is named drift.
--owner-state <state.json>: also step 5 on a copy of that state and of the three rule files in a temporary home.
"""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
COPIES = ("AGENTS.md", ".codex/AGENTS.md", ".claude/CLAUDE.md")
checks = []


def check(name, good, detail=""):
    checks.append(good)
    print(("ok   " if good else "FAIL ") + name + ("" if good or not detail else ": " + detail.strip()[-600:]))


def sdd(home, *args, repo=ROOT, cwd=None):
    env = dict(os.environ, HOME=home, PYTHONPATH=repo)
    p = subprocess.run([sys.executable, "-m", "solo_sdd", *args], cwd=cwd or repo, env=env, capture_output=True,
                       text=True, stdin=subprocess.DEVNULL, timeout=300)
    return p.returncode, p.stdout + p.stderr


def files(home):
    out = {}
    for rel in COPIES:
        p = os.path.join(home, rel)
        if os.path.exists(p):
            with open(p, "rb") as f:
                out[rel] = f.read()
    return out


def home(tmp, name):
    h = os.path.join(tmp, name)
    for d in (".claude", ".codex"):
        os.makedirs(os.path.join(h, d))
    return h


def rule_rows(out):
    return [l.split()[0] for l in out.splitlines() if "global/AGENTS.md" in l]


def owner(tmp, state_path):
    h = os.path.join(tmp, "owner")
    data = os.path.join(h, ".local/share/solo-sdd")
    os.makedirs(data)
    shutil.copy(state_path, os.path.join(data, "state.json"))
    real = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(state_path)))))
    for rel in COPIES:
        if os.path.exists(os.path.join(real, rel)):
            os.makedirs(os.path.dirname(os.path.join(h, rel)), exist_ok=True)
            shutil.copy(os.path.join(real, rel), os.path.join(h, rel))
    with open(os.path.join(data, "state.json")) as f:
        recorded = [k for k in json.load(f) if k in ("~/AGENTS.md", "~/.codex/AGENTS.md", "~/.claude/CLAUDE.md")]
    p = subprocess.run([sys.executable, os.path.join(ROOT, "sync.py"), "push"], env=dict(os.environ, HOME=h),
                       capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=300)
    code, out = sdd(h, "status")
    rows = rule_rows(out)
    check("5 owner state copy (%d block copies recorded): sync.py push, status of the global block %s"
          % (len(recorded), " ".join(rows)), recorded != [] and rows == ["ok"] * len(recorded), p.stdout + out)


with tempfile.TemporaryDirectory(prefix="rules-opt-in-") as tmp:
    new = home(tmp, "new")
    code, out = sdd(new, "install")
    check("1 new home: install exit 0, no global rules file", code == 0 and files(new) == {}, out)

    old = home(tmp, "old")
    with open(os.path.join(old, "AGENTS.md"), "wb") as f:
        f.write(b"my own home rules\n")
    before = files(old)
    base = subprocess.run(["git", "-C", ROOT, "merge-base", "HEAD", "main"], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL).stdout.strip()
    released = os.path.join(tmp, "released")
    os.makedirs(released)
    archive = subprocess.run(["git", "-C", ROOT, "archive", base], capture_output=True, stdin=subprocess.DEVNULL)
    subprocess.run(["tar", "-x", "-C", released], input=archive.stdout, check=True)
    code, out = sdd(old, "install", repo=released)
    check("2 old home: released %s laid out the block in %d files" % (base[:7], len(files(old))),
          code == 0 and len(files(old)) == 3, out)
    newer = os.path.join(tmp, "newer")  # the branch with a newer rules text, so the update is visible
    for d in ("solo_sdd", "global", "skills", "templates", "integrations"):
        shutil.copytree(os.path.join(ROOT, d), os.path.join(newer, d), ignore=shutil.ignore_patterns("__pycache__"))
    for f in ("targets.json", "sync.py", "ALGORITHM.md"):
        shutil.copy(os.path.join(ROOT, f), newer)
    with open(os.path.join(newer, "global/AGENTS.md"), "a", encoding="utf-8") as f:
        f.write("\nA newer rule.\n")
    code, out = sdd(old, "install", repo=newer)
    updated = [l for l in out.splitlines() if l.startswith("updated") and "global/AGENTS.md" in l]
    got = files(old)
    check("2 old home: branch install without the flag updated %d block copies" % len(updated),
          code == 0 and len(updated) == 3 and all(b"A newer rule." in v for v in got.values()), out)
    code, out = sdd(old, "status", repo=newer)
    check("2 old home: status of the global block %s" % " ".join(rule_rows(out)), rule_rows(out) == ["ok"] * 3, out)
    code, out = sdd(old, "uninstall", "--global-rules", repo=newer)
    check("2 old home: uninstall --global-rules, files byte for byte as before the first install",
          code == 0 and files(old) == before, out)
    code, out = sdd(old, "install", repo=newer)
    check("2 old home: a later install writes no global rules", code == 0 and files(old) == before, out)

    proj = os.path.join(tmp, "proj")
    subprocess.run(["git", "init", "-q", proj], check=True, stdin=subprocess.DEVNULL)
    own = "# Team rules\n\nOur own text.\n"
    with open(os.path.join(proj, "AGENTS.md"), "w", encoding="utf-8") as f:
        f.write(own)
    code, out = sdd(new, "init", "--yes", cwd=proj)
    with open(os.path.join(proj, "AGENTS.md"), encoding="utf-8", newline="") as f:
        text = f.read()
    with open(os.path.join(ROOT, "global/AGENTS.md"), encoding="utf-8") as f:
        rules = f.read()
    with open(os.path.join(proj, "CLAUDE.md"), encoding="utf-8") as f:
        claude = f.read()
    block = "<!-- solo-sdd:begin -->\n" + rules + "<!-- solo-sdd:end -->\n"
    check("3 project: init keeps the own text at the start, the block at the end, CLAUDE.md is @AGENTS.md",
          code == 0 and text.startswith(own) and text.endswith(block) and claude == "@AGENTS.md\n", out)
    edited = text.replace("## 3. What \"done\" means", "## 3. What \"done\" means (edited)")
    with open(os.path.join(proj, "AGENTS.md"), "w", encoding="utf-8", newline="") as f:
        f.write(edited)
    code, out = sdd(new, "init", "--reconfigure", "--yes", cwd=proj)
    with open(os.path.join(proj, "AGENTS.md"), encoding="utf-8", newline="") as f:
        after = f.read()
    check("3 project: edited block kept after init --reconfigure, drift named",
          edited != text and after == edited and "drift   AGENTS.md" in out, out)

    if sys.argv[1:2] == ["--owner-state"]:
        owner(tmp, sys.argv[2])

fails = checks.count(False)
print("rules-opt-in: %d of %d checks passed" % (len(checks) - fails, len(checks)))
sys.exit(1 if fails else 0)
