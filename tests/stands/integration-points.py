#!/usr/bin/python3
"""Live scenario of change integration-points, steps 1-7: the `stop` hook, `solo-sdd check --change` and the laid-out
skills, on a temporary git project and a temporary HOME.

The project holds an open change marker-demo and the fictional marker-check (`mode: gate`, `applies: *.py`): its
check.sh reads the changed files on stdin, exits 1 when one holds a line FORBIDDEN and appends a line to a counter
file outside the project on every start. The hook is global/work_hooks.py of this tree, run as a process the way
Claude Code runs it; PATH holds a `solo-sdd` command running the package of this tree. Step 8 of the scenario (the
whole suite) is the suite command itself, not run here. Run from the repository root: python3
tests/stands/integration-points.py. The temporary folder is removed; the last line is the summary."""
import json, os, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
HOOK = ROOT / "global" / "work_hooks.py"
MARKER = ('name: marker-check\nabout: refuses a marker line\npoints: checks, ship\n'
          'command: sh "$SOLO_SDD_INTEGRATION_DIR/check.sh"\napplies: *.py\nmode: gate\n')
FORBID = ('while read -r f; do if grep -qx FORBIDDEN "$f" 2>/dev/null; then echo "marker in $f"; exit 1; fi; done\n'
          'echo "no marker"\n')
VERIFICATION = ("## Live Scenario\n\nthe stand\n\n## Needs\n\nnone\n\n## Fallback\n\nnot needed.\n\n## Result\n\n"
                "<!-- Filled during apply -->\n\n2026-11-12: a line of the author.\n\n## Not Verified\n\nnothing\n")
RUN = "solo-sdd check --point checks --changed"
LINE = re.compile(r"^Integrations checks \(tree ([0-9a-f]{40})\): (.*)$", re.M)
passed, total = 0, 0


def step(name, good, detail):
    global passed, total
    total += 1
    passed += bool(good)
    print("%s %s: %s" % ("ok" if good else "FAIL", name, str(detail).strip().replace("\n", " | ")[:300]))


def main():
    tmp = tempfile.mkdtemp(prefix="integration-points-")
    try:
        proj, home, bindir = (os.path.join(tmp, n) for n in ("proj", "home", "bin"))
        counter = os.path.join(tmp, "counter")
        for d in (os.path.join(proj, "solo-sdd", "specs"), home, bindir):
            os.makedirs(d)
        with open(os.path.join(bindir, "solo-sdd"), "w") as f:
            f.write("#!/bin/sh\nPYTHONPATH=%s exec %s -m solo_sdd \"$@\"\n" % (ROOT, sys.executable))
        os.chmod(os.path.join(bindir, "solo-sdd"), 0o755)
        env = {"PATH": bindir + ":/usr/bin:/bin", "HOME": home, "LANG": "C.UTF-8"}
        integ = os.path.join(proj, "solo-sdd", "integrations", "marker-check")
        vpath = os.path.join(proj, "solo-sdd", "changes", "marker-demo", "verification.md")
        log = os.path.join(home, ".claude", "hook-state", "errors.log")

        def put(path, text):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(text)

        def read(path):
            try:
                with open(path) as f:
                    return f.read()
            except FileNotFoundError:
                return ""

        def git(*args):
            return subprocess.run(["git", "-c", "user.name=stand", "-c", "user.email=stand@example.com", "-c",
                                   "commit.gpgsign=false", *args], cwd=proj, env=env, capture_output=True, text=True,
                                  stdin=subprocess.DEVNULL, check=True).stdout

        def sdd(*args):
            p = subprocess.run(["solo-sdd", *args], cwd=proj, env=env, capture_output=True, text=True, timeout=120,
                               stdin=subprocess.DEVNULL)
            return p.returncode, p.stdout + p.stderr

        sessions = iter(range(1000))
        transcript = os.path.join(tmp, "transcript.jsonl")

        def edit(text):
            put(os.path.join(proj, "app.py"), text)
            put(transcript, json.dumps({"type": "assistant", "message": {"content": [
                {"type": "tool_use", "name": "Edit", "input": {"file_path": os.path.join(proj, "app.py")}}]}}) + "\n")

        def stop():
            """The integration lines of the `stop` hook's reason (a new session each call), and the whole output."""
            inp = {"session_id": "stand-%d" % next(sessions), "cwd": proj, "transcript_path": transcript,
                   "last_assistant_message": "Done."}
            p = subprocess.run([sys.executable, str(HOOK), "stop"], input=json.dumps(inp), env=env,
                               capture_output=True, text=True, timeout=120)
            out = json.loads(p.stdout) if p.stdout.strip() else {}
            return [ln for ln in out.get("reason", "").splitlines() if "apply to this session's edits" in ln], p.stdout

        def starts():
            return len(read(counter).splitlines())

        put(os.path.join(integ, "integration"), MARKER)
        put(os.path.join(integ, "check.sh"), "echo x >> %s\n%s" % (counter, FORBID))
        put(os.path.join(proj, "solo-sdd", "config"), "integrations: marker-check\n")
        put(vpath, VERIFICATION)
        git("init", "-q", "-b", "main")
        git("add", "-A")
        git("commit", "-q", "-m", "base")

        edit("x = 1\n")
        found, out = stop()
        step("1 stop after an edit without a run", len(found) == 1 and "`%s`" % RUN in found[0],
             "the reason names `%s`" % RUN if found else out)

        code, out = sdd("check", "--point", "checks", "--changed", "--change", "marker-demo")
        lines = LINE.findall(read(vpath))
        step("2 check --change marker-demo", code == 0 and len(lines) == 1 and lines[0][1] == "marker-check PASS",
             "code %d, %d Integrations checks line: %s" % (code, len(lines), lines[0][1] if lines else "-"))

        found, out = stop()
        step("3 stop on the same tree", found == [] and "uncommitted edits" in out, found or "no integration reason")

        edit("x = 2\n")
        code, out = sdd("check", "--point", "checks", "--changed", "--change", "marker-demo")
        again = LINE.findall(read(vpath))
        kept = [ln for ln in read(vpath).split("\n") if not ln.startswith("Integrations ")] == VERIFICATION.split("\n")
        step("4 a second run after an edit", code == 0 and len(again) == 1 and again[0][0] != lines[0][0] and kept,
             "code %d, %d line, a new hash: %s, the other lines kept: %s" % (
                 code, len(again), bool(again and lines and again[0][0] != lines[0][0]), kept))

        before = starts()
        code, out = sdd("check", "--point", "checks", "--change", "no-such")
        step("5 an unknown change", code == 1 and "no-such" in out and starts() == before,
             "code %d, %s; integration starts %d -> %d" % (code, out.strip(), before, starts()))

        edit("x = 3\n")
        lines_before = len(read(log).splitlines())
        put(os.path.join(integ, "integration"), MARKER + "nosuchkey: 1\n")
        found, out = stop()
        new = read(log).splitlines()[lines_before:]
        step("6 a broken description in the hook", found == [] and len(new) == 1 and "nosuchkey" in new[0],
             "no integration reason, %d errors.log line naming nosuchkey" % len(new) if new else "no errors.log line")

        p = subprocess.run([sys.executable, "sync.py", "push", "--global-rules"], cwd=ROOT, env=env,
                           capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL)
        skills = {n: read(os.path.join(home, ".claude", "skills", n, "SKILL.md")) for n in ("spec-next", "ship")}
        flat = {n: re.sub(r"\s+", " ", t) for n, t in skills.items()}
        step6 = flat["spec-next"].split(" 6. **Checks**", 1)[-1].split(" 7. **Live test**", 1)[0]
        step7a = flat["spec-next"].split(" 7a. ", 1)[-1].split(" 8. ", 1)[0]
        ship = flat["ship"].split(" 3. **Inventory.**", 1)[-1].split(" 5. **Commits.**", 1)[0]
        want = [("spec-next step 6", step6, "`solo-sdd check --point checks --changed --change <id>`"),
                ("spec-next step 6", step6, "Code 1 (a `gate` FAIL) holds the step as a red test does"),
                ("spec-next step 7a", step7a, "the printed lines of the last `solo-sdd check` run of step 6, `advice` "
                                              "lines included"),
                ("spec-next step 7a", step7a, "does not rerun `solo-sdd check` or any integration"),
                ("ship step 3", ship, "then `solo-sdd check --point ship`"),
                ("ship step 3", ship, "Code 1 (a `gate` FAIL) stops before the commit")]
        missing = ["%s: %s" % (n, w) for n, text, w in want if w not in text]
        step("7 the laid-out skills", p.returncode == 0 and not missing,
             "push code %d; %s" % (p.returncode, missing or "%d phrases found" % len(want)))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("integration-points: %d of %d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
