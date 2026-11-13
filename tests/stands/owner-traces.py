#!/usr/bin/env python3
"""Live scenario of change owner-traces, without model calls.

1. The texts of the commit before this change (ALGORITHM.md, global/AGENTS.md, skills/*/SKILL.md from git) name
   skills that are neither shipped nor optional tools: the list holds personal skills such as `demo-brief`.
2. `HOME=$T/home solo-sdd install`: every skill the deployed SKILL.md files, ALGORITHM.md and global rules name is a
   deployed skill or a README optional tool (no humanizer-ru in the temporary home).
3. The deployed copy-check checks a non-English string by the facts audit and names no personal skill.
4. The deployed debug-profile has its own diagnosis steps and names no plugin skill (a backquoted `plugin:name`).
5. No "the owner" in the deployed skills, algorithm, global rules and templates, except the quoted program output
   "waits for the owner: <paths>"; no `Desktop` in the deployed hooks.
Run from the repository root: python3 tests/stands/owner-traces.py. The temporary folder is removed; the last line
is "total: N of N", code 0 only if every step matched."""
import os, pathlib, re, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from test_public_tree import optional_tools, refs_in  # noqa: E402

PR_WAIT = "waits for the owner: <paths>"  # literal output of sdd_pr.py and sdd_dispatch.py, quoted by spec-dispatch
ENV = {k: v for k, v in os.environ.items() if k != "HOME"}
results = []


def step(name, good, detail):
    results.append(good)
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout


def base_commit():
    """Parent of the commit that archived this change; before the archive, the fork point from main."""
    c = git("log", "-1", "--format=%H", "--", "solo-sdd/changes/archive/*-owner-traces").strip()
    if c:
        return git("rev-parse", c + "^").strip()
    return git("merge-base", "HEAD", "main").strip() or git("merge-base", "HEAD", "origin/main").strip()


base = base_commit()
files = git("ls-tree", "-r", "--name-only", base, "--", "skills", "ALGORITHM.md", "global/AGENTS.md").split()
shipped = {p.split("/")[1] for p in files if p.startswith("skills/") and p.count("/") >= 2}
known = shipped | optional_tools(ROOT, git("show", base + ":README.md"))
texts = [p for p in files if re.fullmatch(r"skills/[^/]+/SKILL\.md", p) or p in ("ALGORITHM.md", "global/AGENTS.md")]
before = [f for p in texts for f in refs_in(p, git("show", "%s:%s" % (base, p)), known)]
names = {f.rsplit(" ", 1)[1].lstrip("/") for f in before}
step("1 before the change", "demo-brief" in names and len(names) >= 2,
     "%s: %s" % (base[:7], ", ".join(before) or "no findings"))

with tempfile.TemporaryDirectory() as t:
    home = pathlib.Path(t) / "home"
    p = subprocess.run([sys.executable, "-m", "solo_sdd", "install"], cwd=ROOT, env={**ENV, "HOME": str(home)},
                       capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=300)
    skills = home / ".claude" / "skills"
    deployed = {d.name for d in skills.iterdir() if d.is_dir()} if skills.is_dir() else set()
    docs = sorted(skills.glob("*/SKILL.md")) + [home / ".local/share/solo-sdd/ALGORITHM.md", home / ".claude/CLAUDE.md"]
    docs = [d for d in docs if d.is_file()]
    after = [f for d in docs for f in refs_in(str(d.relative_to(home)), d.read_text(encoding="utf-8"),
                                              deployed | optional_tools(ROOT))]
    step("2 deployed references", p.returncode == 0 and len(docs) > 20 and not after,
         "install code %d, %d texts, %d skills, unknown skills: %s"
         % (p.returncode, len(docs), len(deployed), ", ".join(after) or "none"))
    step("2 no personal skills deployed", not ({"humanizer-ru", "demo-brief"} & deployed), "humanizer-ru, demo-brief absent")

    cc = (skills / "copy-check/SKILL.md").read_text(encoding="utf-8")
    other = cc.split("## Other languages and a style skill", 1)[-1].split("\n## ", 1)[0]
    step("3 copy-check other languages", "facts audit" in other and "humanizer" not in cc and "post-draft" not in cc
         and "| What | English | Other languages |" in cc,
         "section found: %s, humanizer named: %s" % ("facts audit" in other, "humanizer" in cc))

    dp = (skills / "debug-profile/SKILL.md").read_text(encoding="utf-8")
    sp = [m.group() for m in re.finditer(r"`([a-z][a-z0-9-]*):[a-z0-9-]+[^`]*`", dp) if m.group(1) != "file"]
    step("4 debug-profile own steps", "## 2. Diagnosis" in dp and not sp,
         "%d diagnosis steps, plugin skills: %s"
         % (len(re.findall(r"^\d\. \*\*", dp.split("## 2. Diagnosis")[-1].split("\n## ")[0], re.M)),
            ", ".join(sp) or "none"))

    # the texts this change owns: skills, algorithm, global rules, templates (vendor copies are third-party text)
    every = docs + [f for f in home.rglob("templates/**/*") if f.is_file()]
    owner = ["%s:%d" % (f.relative_to(home), n) for f in every
             for n, l in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1)
             if re.search(r"\b[Tt]he owner\b", l.replace(PR_WAIT, ""))]
    hooks = [f for f in (home / ".claude/hooks").glob("*.py") if "Desktop" in f.read_text(encoding="utf-8")]
    step("5 no owner traces", not owner and not hooks,
         "'the owner' lines: %s; hooks with Desktop: %s" % (", ".join(owner[:5]) or "none",
                                                            ", ".join(h.name for h in hooks) or "none"))

print("total: %d of %d" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
