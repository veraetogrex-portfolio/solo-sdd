#!/usr/bin/env python3
"""What a skill gives the current main model, measured by switching it off (Requirements: Skills audit table, Ablation
runner, Ablation grade, Grade outcomes, Runner input refused, Full skill out of reach in the cut variants).

  prepare <skill> --budget <calls> [--out <dir>]   one prompt per variant, task by task, in a new run folder
  grade <run> [--from <subagents dir>]             the table of a run whose prompts the lead ran as subagents
  remove <run>                                     the run folder and its work folders, after the table is recorded
  audit                                            the docs/skills-audit.md check the tests run

Model runs never start here: the lead session runs every prompt as an `Agent` subagent under the description the
prompt names (never `claude -p`) and passes its subagents folder to `grade --from`.
"""
import argparse
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tests"))
import skill_text  # noqa: E402

VARIANTS = ("full", "cut", "none")
MARKS = ("gate (code)", "gate (text)", "method")
GATES = "Gates a hook could hold"
CANDIDATE = "candidate to cut: the owner decides"
LIMIT = 64 * 1024 * 1024
NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
ITEM = re.compile(r"^(\*\*)?(\d+[a-z]?)\.(?:\*\*)?\s+(.*)$")
HEAD = re.compile(r"^#{1,6}\s+(.*?)\s*#*\s*$")
COMPARE = re.compile(r"compare: full (\d+) of (\d+), cut (?:\d+|-) of \d+, none (\d+) of \d+")


def sets_dir(root):
    return pathlib.Path(root) / "tests/stands/skill-ablation"


def target_skills(root=REPO):
    return sorted(json.loads((pathlib.Path(root) / "targets.json").read_text(encoding="utf-8"))["skills"])


def title(bold, rest):
    """The title of a step line: its bold part, else its text up to a colon, a full stop or a bracket, at most 6
    words; backquotes and pipes dropped, so it fits a table cell."""
    if bold:
        t = rest.split("**", 1)[0]
    elif rest.startswith("**"):
        t = rest[2:].split("**", 1)[0]
    else:
        t = re.split(r":|\. |\(", rest, maxsplit=1)[0]
    return " ".join(t.replace("`", "").replace("|", "").strip().rstrip(".:").split()[:6])


def steps(name, root=REPO):
    """[(heading, step, first line, end line)] of skills/<name>/SKILL.md: a top-level `N.`, `Na.` or `**N.` item outside
    fenced code, up to the next item or heading; a skill without items has one ("", "whole text") step."""
    lines = (pathlib.Path(root) / "skills" / name / "SKILL.md").read_text(encoding="utf-8").splitlines()
    out, heading, fence = [], "", False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            fence = not fence
            continue
        if fence:
            continue
        h, m = HEAD.match(line), ITEM.match(line)
        if (h or m) and out and out[-1][3] is None:
            out[-1][3] = i
        if h:
            heading = h.group(1)
        elif m:
            out.append([heading, "%s. %s" % (m.group(2), title(m.group(1), m.group(3))), i, None])
    if not out:
        return [("", "whole text", 0, len(lines))]
    if out[-1][3] is None:
        out[-1][3] = len(lines)
    return [tuple(s) for s in out]


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def table(root=REPO):
    """{"skills": {name: {"rows": {(heading, step): (mark, hook)}, "runs": [(full, n, none)], "candidate": bool}},
    "gates": {(skill, heading, step)}, "order": [section names]} read from docs/skills-audit.md; a section's step table
    is the table before its first `###` part, a run is a `compare:` line inside its `### Run` parts."""
    text = (pathlib.Path(root) / "docs/skills-audit.md").read_text(encoding="utf-8")
    out = {"skills": {}, "gates": set(), "order": []}
    cur, part = None, None
    for line in text.splitlines():
        if line.startswith("## "):
            cur, part = line[3:].strip(), None
            out["order"].append(cur)
            if cur != GATES:
                out["skills"][cur] = {"rows": {}, "runs": [], "candidate": False}
            continue
        if cur is None:
            continue
        if line.startswith("### "):
            part = line[4:].strip()
            continue
        if cur == GATES:
            c = cells(line) if line.startswith("|") else []
            if len(c) >= 3 and c[0].startswith("`") and c[0].endswith("`"):
                out["gates"].add((c[0].strip("`"), c[1], c[2]))
            continue
        sec = out["skills"][cur]
        if CANDIDATE in line:
            sec["candidate"] = True
        m = COMPARE.search(line)
        if m and part and part.startswith("Run "):
            sec["runs"].append((int(m.group(1)), int(m.group(2)), int(m.group(3))))
        if part is None and line.startswith("|"):
            c = cells(line)
            if len(c) >= 4 and c[0] != "Heading" and not re.fullmatch(r":?-+:?", c[0]):
                sec["rows"][(c[0], c[1])] = (c[2], c[3])
    return out


def lost_twice(runs):
    """True when the last two runs with a compared task each have full passes no more than none passes."""
    real = [r for r in runs if r[1] > 0]
    return len(real) >= 2 and all(full <= none for full, _, none in real[-2:])


def audit_errors(root=REPO):
    """The `skills-audit: ...` lines for every way docs/skills-audit.md misses the skills of targets.json."""
    t = table(root)
    errors = []
    names = target_skills(root)
    for name in names:
        sec = t["skills"].get(name)
        if sec is None:
            errors.append("skills-audit: no section for %s" % name)
            continue
        keys = [(h, s) for h, s, _, _ in steps(name, root)]
        errors += ["skills-audit: %s: no row for %s / %s" % (name, h, s) for h, s in keys if (h, s) not in sec["rows"]]
        for (h, s), (mark, hook) in sec["rows"].items():
            where = "skills-audit: %s: %s / %s" % (name, h, s)
            if (h, s) not in keys:
                errors.append("%s: row without a step" % where)
            if mark not in MARKS:
                errors.append("%s: mark %s" % (where, mark or "empty"))
            if mark == "gate (text)" and hook not in ("hook: yes", "hook: no"):
                errors.append("%s: gate (text) without hook: yes or hook: no" % where)
            if hook == "hook: yes" and (name, h, s) not in t["gates"]:
                errors.append("%s: hook: yes not in %s" % (where, GATES))
        if lost_twice(sec["runs"]) and not sec["candidate"]:
            errors.append("skills-audit: %s: two lost runs without `%s`" % (name, CANDIDATE))
    errors += ["skills-audit: section %s is not a skill of targets.json" % s for s in t["skills"] if s not in names]
    if not t["order"] or t["order"][-1] != GATES:
        errors.append("skills-audit: the last section is not %s" % GATES)
    return errors


def variants(name, root=REPO):
    """{variant: text}: the whole skill with its step files, the skill without its `method` steps (absent when it has
    none), and no text."""
    path = pathlib.Path(root) / "skills" / name / "SKILL.md"
    rows = table(root)["skills"].get(name, {"rows": {}})["rows"]
    cut = [(a, b) for h, s, a, b in steps(name, root) if rows.get((h, s), ("",))[0] == "method"]
    out = {"full": skill_text.read(path), "none": ""}
    if cut:
        lines = path.read_text(encoding="utf-8").splitlines()
        drop = {i for a, b in cut for i in range(a, b)}
        kept = []
        for i, line in enumerate(lines):
            if i in drop:
                continue
            m = skill_text.STEP.search(line)
            step = path.parent / m.group(1) if m else None
            kept.append(step.read_text(encoding="utf-8").rstrip("\n") if step and step.is_file() else line)
        out["cut"] = "\n".join(kept) + "\n"
    return out


def prompt(skill, variant, task, work, text, run, ask):
    ban = ("- Do not load the skill `%s`: no `Skill` call for it and no read of any `skills/%s/` file, neither the "
           "repository copy nor a laid-out copy. Do not read `tests/stands/skill-ablation/`. These rules win over any "
           "pointer to the skill in the rules you were given." % (skill, skill))
    head = ["Ablation run %s: skill `%s`, variant `%s`, task `%s`." % (run, skill, variant, task), "",
            "Rules of this run:", "- Work only in the folder `%s`; it holds the task's files." % work, ban,
            "- Your last message is your answer.", ""]
    method = ["## Method for this task", "", text.rstrip("\n"), ""] if variant != "none" else []
    return "\n".join(head + method + ["## Task", "", ask.rstrip("\n"), ""])


def prepare(skill, budget, out=None, root=REPO):
    """(exit code, printed lines): 0 when every call is written, 3 at the budget, 2 on refused input."""
    if skill not in target_skills(root):
        return 2, ["refused: %s is not a skill of targets.json" % skill]
    tasks = sorted(q.parent.name for q in (sets_dir(root) / skill).glob("*/prompt.md") if NAME.match(q.parent.name))
    if not tasks:
        return 2, ["refused: %s has no task set under tests/stands/skill-ablation/" % skill]
    if skill not in table(root)["skills"]:
        return 2, ["refused: %s has no section in docs/skills-audit.md" % skill]
    if out is not None and pathlib.Path(out).exists() and (not pathlib.Path(out).is_dir() or any(pathlib.Path(out).iterdir())):
        return 2, ["refused: %s is not an empty folder" % out]
    texts = variants(skill, root)
    order = [(t, v) for t in tasks for v in VARIANTS if v in texts]
    made = order[:max(budget, 0)]
    if out is None:
        run = pathlib.Path(tempfile.mkdtemp(prefix="skill-ablation-%s-" % skill))
    else:
        run = pathlib.Path(out)
        run.mkdir(parents=True, exist_ok=True)
    run = run.resolve()
    lines = ["run: %s" % run]
    for t in sorted({t for t, _ in made}):
        src, dst = sets_dir(root) / skill / t, run / "checks" / t
        dst.mkdir(parents=True)
        for f in ("prompt.md", "check.py", "required.txt"):
            shutil.copy2(src / f, dst / f)
    prompts = []
    for t, v in made:
        pid = "%s-%s" % (t, v)
        # each work folder in a temporary folder of its own: nothing of the run (prompts, checks) or of another
        # variant lies next to it
        work = pathlib.Path(tempfile.mkdtemp(prefix="skill-ablation-work-%s-" % pid)).resolve() / "work"
        shutil.copytree(sets_dir(root) / skill / t / "fixture", work)
        desc = "Ablation: %s %s %s %s" % (skill, v, t, run.name)
        ask = (run / "checks" / t / "prompt.md").read_text(encoding="utf-8")
        (run / (pid + ".prompt.md")).write_text(prompt(skill, v, t, work, texts[v], run.name, ask), encoding="utf-8")
        prompts.append({"id": pid, "task": t, "variant": v, "description": desc, "work": str(work.parent)})
        lines.append("prompt: %s | description: %s | work: %s" % (run / (pid + ".prompt.md"), desc, work))
    manifest = {"skill": skill, "run": run.name, "variants": [v for v in VARIANTS if v in texts], "tasks": tasks,
                "prompts": prompts, "total": len(order), "not_made": len(order) - len(made)}
    (run / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    if len(made) < len(order):
        lines.append("budget reached: %d of %d calls not made" % (len(order) - len(made), len(order)))
        return 3, lines
    return 0, lines


def remove(run):
    """Remove a run folder and the work folders its manifest names; the stand and the tests use it."""
    run = pathlib.Path(run)
    try:
        prompts = json.loads((run / "manifest.json").read_text(encoding="utf-8"))["prompts"]
    except (OSError, ValueError, KeyError):
        prompts = []
    for p in prompts:
        work = pathlib.Path(p.get("work", ""))
        if work.name.startswith("skill-ablation-work-"):
            shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(run, ignore_errors=True)


def read_manifest(run, root):
    """The manifest when every field is one prepare writes, else None."""
    try:
        m = json.loads((run / "manifest.json").read_text(encoding="utf-8"))
        ok = (isinstance(m, dict) and m["skill"] in target_skills(root) and isinstance(m["prompts"], list)
              and m["variants"] in (list(VARIANTS), ["full", "none"]) and isinstance(m["tasks"], list)
              and all(isinstance(t, str) and NAME.match(t) for t in m["tasks"])
              and isinstance(m["not_made"], int) and isinstance(m["run"], str))
        for p in m["prompts"] if ok else ():
            ok = ok and isinstance(p, dict) and (p["variant"] in m["variants"] and p["task"] in m["tasks"]
                         and p["id"] == "%s-%s" % (p["task"], p["variant"]) and isinstance(p["description"], str)
                         and (run / "checks" / p["task"] / "check.py").is_file())
        return m if ok else None
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return None


def by_description(folder):
    """{description: [transcript paths]} of the regular agent-*.jsonl files of a subagents folder whose regular
    meta.json reads; links and broken meta files are skipped."""
    out = {}
    for meta in sorted(pathlib.Path(folder).glob("agent-*.meta.json")):
        jsonl = meta.with_name(meta.name[:-len(".meta.json")] + ".jsonl")
        if meta.is_symlink() or jsonl.is_symlink() or not jsonl.is_file():
            continue
        try:
            desc = json.loads(meta.read_text(encoding="utf-8"))["description"]
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if isinstance(desc, str):
            out.setdefault(desc, []).append(jsonl)
    return out


def read_transcript(path):
    """(calls [(tool, input)], answer or None, models, tokens or None, error or None) of a Claude Code transcript."""
    if path.stat().st_size > LIMIT:
        return [], None, set(), None, "over %d bytes" % LIMIT
    calls, answer, models, tokens, last_text = [], None, set(), None, None
    with path.open(encoding="utf-8", errors="replace") as f:
        for n, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                d = json.loads(line)
            except ValueError:
                return [], None, set(), None, "line %d is not JSON" % n
            if not isinstance(d, dict) or d.get("type") != "assistant" or not isinstance(d.get("message"), dict):
                continue
            msg = d["message"]
            if isinstance(msg.get("model"), str):
                models.add(msg["model"])
            u = msg.get("usage")
            if isinstance(u, dict):
                tokens = sum(u.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens",
                                                       "cache_read_input_tokens", "output_tokens")
                             if isinstance(u.get(k) or 0, int))
            for b in msg.get("content") if isinstance(msg.get("content"), list) else ():
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use":
                    inp = b.get("input") if isinstance(b.get("input"), dict) else {}
                    calls.append((str(b.get("name")), inp))
                    if b.get("name") == "SubagentHandback" and isinstance(inp.get("message"), str):
                        answer = inp["message"]
                elif b.get("type") == "text" and isinstance(b.get("text"), str) and b["text"].strip():
                    last_text = b["text"]
    return calls, answer if answer is not None else last_text, models, tokens, None


def leaked(skill, calls, run=None):
    """True when a call loads the skill, names its folder (`skills/<skill>`, any copy), the task sets or the run
    folder that holds the prompts with the full text and the checks."""
    near = [re.escape("skills/" + skill), re.escape("tests/stands/skill-ablation")]
    if run is not None:
        near += [re.escape(str(run)), re.escape(re.sub(r"^/private(?=/)", "", str(run)))]
    pattern = re.compile(r"(?:%s)(?![A-Za-z0-9_.-])" % "|".join(near))
    for name, inp in calls:
        if name == "Skill" and str(inp.get("skill", "")).split(":")[-1] == skill:
            return True
        if pattern.search(json.dumps(inp, sort_keys=True)):
            return True
    return False


def judge(skill, path, checks, ans, run=None):
    """(outcome, path, tokens, note, models) of one transcript, first match wins: unreadable, not run, leaked, pass
    (the check exits 0 on the answer file and every required call is there), fail. The answer goes to ans."""
    calls, answer, models, tok, err = read_transcript(path)
    tokens = "-" if tok is None else str(tok)
    required = [l.strip() for l in (checks / "required.txt").read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.strip().startswith("#")]
    texts = ["%s %s" % (n, json.dumps(i, sort_keys=True)) for n, i in calls]
    hit = sum(any(re.search(r, t) for t in texts) for r in required)
    req = "%d of %d" % (hit, len(required))
    if err:
        return "unreadable", "-", tokens, err, models
    if not answer or not answer.strip():
        return "not run", req, tokens, "", models
    if leaked(skill, calls, run):
        return "leaked", req, tokens, "", models
    if ans.is_symlink():
        ans.unlink()
    ans.write_text(answer, encoding="utf-8")
    ok = check(checks, ans) and hit == len(required)
    return ("pass" if ok else "fail"), req, tokens, "", models


def check(checks, ans):
    """True when the task's check.py exits 0 on the answer file; the answer is an argument, never run."""
    try:
        return subprocess.run([sys.executable, "-I", "check.py", str(ans)], cwd=checks, stdin=subprocess.DEVNULL,
                              capture_output=True, timeout=60).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def task_errors(root=REPO):
    """`task set <skill>/<task>: ...` for every task folder that misses a file, whose reference.jsonl does not grade
    `pass`, or whose check.py passes an empty answer."""
    errors = []
    for task in sorted(p.parent for p in sets_dir(root).glob("*/*/prompt.md")):
        name = "task set %s/%s" % (task.parent.name, task.name)
        missing = [f for f in ("check.py", "required.txt", "reference.jsonl", "fixture") if not (task / f).exists()]
        if missing:
            errors.append("%s: no %s" % (name, ", ".join(missing)))
            continue
        with tempfile.TemporaryDirectory() as d:
            ans = pathlib.Path(d) / "answer.md"
            outcome = judge(task.parent.name, task / "reference.jsonl", task, ans)[0]
            if outcome != "pass":
                errors.append("%s: reference.jsonl grades %s" % (name, outcome))
            ans.write_text("", encoding="utf-8")
            if check(task, ans):
                errors.append("%s: check.py passes an empty answer" % name)
    return errors


def grade(run, src=None, root=REPO):
    """(exit code, printed lines) of a run folder: one row per prompt, the models, `compare:` and the counts."""
    run = pathlib.Path(run).resolve()
    m = read_manifest(run, root)
    if m is None:
        return 2, ["refused: %s has no manifest prepare writes" % run]
    found = by_description(src) if src else {}
    rows, models = [], set()
    for p in m["prompts"]:
        pid, path = p["id"], run / (p["id"] + ".jsonl")
        hits = found.get(p["description"], [])
        note = ""
        if src and path.is_symlink():
            path.unlink()
        if src and len(hits) == 1:
            shutil.copyfile(hits[0], path)  # with --from only the subagents folder's transcript counts
        if src and len(hits) > 1:
            outcome, req, tokens, note = "unreadable", "-", "-", "%d transcripts for one description" % len(hits)
        elif (src and not hits) or not path.is_file() or path.is_symlink():
            outcome, req, tokens = "not run", "-", "-"
        else:
            outcome, req, tokens, note, mods = judge(m["skill"], path, run / "checks" / p["task"], run / (pid + ".answer.md"),
                                                   run)
            models |= mods
        rows.append((p["task"], p["variant"], outcome, req, tokens, note))
    lines = ["skill: %s; run: %s" % (m["skill"], m["run"]), "models: %s" % (", ".join(sorted(models)) or "none"),
             "| task | variant | outcome | path | tokens | note |", "|---|---|---|---|---|---|"]
    lines += ["| %s |" % " | ".join(r) for r in rows]
    graded = {(t, v): o for t, v, o, _, _, _ in rows}
    tasks = [t for t in m["tasks"] if all(graded.get((t, v)) in ("pass", "fail") for v in m["variants"])]
    score = {v: sum(graded[(t, v)] == "pass" for t in tasks) for v in m["variants"]}
    n = len(tasks)
    cut = "%d" % score["cut"] if "cut" in score else "-"
    lines.append("compare: full %d of %d, cut %s of %d, none %d of %d" % (score["full"], n, cut, n, score["none"], n))
    count = lambda o: sum(r[2] == o for r in rows)
    lines.append("not run: %d; leaked: %d; unreadable: %d; not made: %d"
                 % (count("not run"), count("leaked"), count("unreadable"), m["not_made"]))
    return 0, lines


def main(argv=None):
    ap = argparse.ArgumentParser(prog="skill-ablation.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("skill")
    p.add_argument("--budget", type=int, required=True)
    p.add_argument("--out")
    g = sub.add_parser("grade")
    g.add_argument("run")
    g.add_argument("--from", dest="src")
    r = sub.add_parser("remove")
    r.add_argument("run")
    sub.add_parser("audit")
    a = ap.parse_args(argv)
    if a.cmd == "prepare":
        code, lines = prepare(a.skill, a.budget, a.out)
    elif a.cmd == "grade":
        code, lines = grade(a.run, a.src)
    elif a.cmd == "remove":
        if not (pathlib.Path(a.run) / "manifest.json").is_file():
            print("refused: %s has no manifest.json" % a.run)
            return 2
        remove(a.run)
        code, lines = 0, ["removed: %s and its work folders" % a.run]
    else:
        lines = audit_errors()
        code = 1 if lines else 0
        lines = lines or ["skills-audit: ok"]
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
