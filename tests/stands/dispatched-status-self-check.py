#!/usr/bin/env python3
"""Stand of change dispatched-status-self-check (Requirement: Status self-check before handback).
A temporary git worktree gets a change archive whose Live Scenario names `python3 stand.py`; the repository's
sdd_dispatch.py accept runs on a paraphrased LIVE line (must refuse with a LIVE: line) and on the printed line
copied verbatim (must print status matches) and on a LIVE command that prints it and exits 3 (must report exit 3);
then the self-check line of the spec-next dispatcher section and of the orchestrator prompt is checked for every rule.
Nothing outside the temporary folder changes."""
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tests"))
import skill_text  # noqa: E402

TOOL = REPO / "global/sdd_dispatch.py"
PRINTED = "demo: 4 of 4 checks passed"


def accept(root, stated, cmd="python3 stand.py"):
    st = root.parent / "status.txt"
    st.write_text("STATUS: archived\nCHANGE: demo\nWORKTREE: %s\nVALIDATE: true -> exit 0\nARCHIVE: arch\n"
                  "LIVE: %s -> %s\n" % (root, cmd, stated), encoding="utf-8")
    r = subprocess.run([sys.executable, str(TOOL), "accept", str(st)], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=120)
    return r.returncode, r.stdout


with tempfile.TemporaryDirectory(prefix="status-self-check-") as d:
    root = pathlib.Path(d) / "wt"
    subprocess.run(["git", "init", "-q", str(root)], check=True, stdin=subprocess.DEVNULL)
    (root / "stand.py").write_text("print('ok   check')\nprint(%r)\n" % PRINTED, encoding="utf-8")
    (root / "failing.py").write_text("print(%r)\nraise SystemExit(3)\n" % PRINTED, encoding="utf-8")
    (root / "arch").mkdir()
    (root / "arch" / "verification.md").write_text("## Live Scenario\n\n1. `python3 stand.py`\n2. `python3 failing.py`\n",
                                                   encoding="utf-8")
    bad = accept(root, "all four checks pass")
    ok = accept(root, PRINTED)
    failing = accept(root, PRINTED, "python3 failing.py")

RULES = {  # every rule of the requirement, looked up only in that file's self-check line
    "spec-next": ("before handing back `archived`", "file outside `WORKTREE`",
                  "`python3 ~/.local/bin/sdd-dispatch.py accept <file>`", "correct the stated field from the real output",
                  "one printed line, copied verbatim", "and repeat", "only after `status matches`",
                  "is not edited into the field", "fix the change and check again",
                  "hand back `not_ready` with the failure in `NOTES`"),
    "orchestrator-prompt": ("before handing back archived", "file outside WORKTREE",
                            "`python3 ~/.local/bin/sdd-dispatch.py accept <file>`",
                            "correct a mismatched field from the real output", "one line of the command's output, copied verbatim",
                            "and repeat", "only after \"status matches\"", "is not edited into the field",
                            "fix the change and check again", "hand back not_ready with the failure in NOTES"),
}


def self_check_line(text, prefix):
    """The one item that starts with prefix, with its continuation lines up to a blank line or the next item,
    whitespace collapsed; empty when there is none or more than one."""
    items, cur = [], None
    for l in text.splitlines():
        if l.startswith(prefix):
            cur = [l]
            items.append(cur)
        elif cur is not None and l.strip() and not l.startswith("- "):
            cur.append(l)
        else:
            cur = None
    return " ".join(" ".join(items[0]).split()) if len(items) == 1 else ""


skill = skill_text.skill("spec-next")
dispatched = skill.partition("\n## Under the dispatcher\n")[2].split("\n## ")[0]  # the bullet must sit in this section
lines = {"spec-next": self_check_line(dispatched, "- Status self-check: "),
         "orchestrator-prompt": self_check_line((REPO / "skills/spec-dispatch/orchestrator-prompt.md").read_text("utf-8"),
                                                "Status self-check: ")}
missing = [(name, r) for name, rules in RULES.items() for r in rules if r not in lines[name]]
checks = [("paraphrased LIVE: exit 1 with a LIVE: mismatch line",
           bad[0] == 1 and any(l.startswith("LIVE: python3 stand.py") and "text missing" in l
                               for l in bad[1].splitlines())),
          ("verbatim LIVE: exit 0, status matches", ok[0] == 0 and ok[1].strip() == "status matches"),
          ("failing LIVE command with the printed line: exit 1, got exit 3",
           failing[0] == 1 and any(l.startswith("LIVE: python3 failing.py") and "got exit 3" in l
                                   for l in failing[1].splitlines())),
          ("each self-check line carries every rule of the requirement%s"
           % "".join("; missing in %s: %s" % m for m in missing), not missing)]
for name, good in checks:
    print(("ok   " if good else "FAIL ") + name)
fails = sum(not g for _, g in checks)
print("dispatched-status-self-check: %d of %d checks passed" % (len(checks) - fails, len(checks)))
sys.exit(1 if fails else 0)
