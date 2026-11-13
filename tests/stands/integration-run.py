#!/usr/bin/python3
"""Live scenario of change integration-run, steps 1-6: `solo-sdd check` on a temporary git project.

A temporary git project with a solo-sdd/ tree and a temporary HOME; PATH is a stand bin folder with a `solo-sdd`
command running the package of this tree with this interpreter, then /usr/bin and /bin. The project holds the
fictional marker-check: its check.sh reads the changed files on stdin, exits 1 when one holds a line FORBIDDEN and
appends a line to a counter file outside the project on every start. Step 7 of the scenario (the whole suite) is the
suite command itself, not run here. Run from the repository root: python3 tests/stands/integration-run.py. The
temporary folder is removed; the last line is the summary."""
import glob, json, os, pathlib, shutil, subprocess, sys, tempfile, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMMAND = 'sh "$SOLO_SDD_INTEGRATION_DIR/check.sh"'
MARKER = "name: marker-check\nabout: refuses a marker line\npoints: checks\ncommand: %s\nmode: gate\n" % COMMAND
FORBID = ('while read -r f; do if grep -qx FORBIDDEN "$f" 2>/dev/null; then echo "marker in $f"; exit 1; fi; done\n'
          'echo "no marker"\n')
passed, total = 0, 0


def step(name, good, detail):
    global passed, total
    total += 1
    passed += bool(good)
    print("%s %s: %s" % ("ok" if good else "FAIL", name, detail.strip().replace("\n", " | ")))


def controls(text):
    return [c for c in text if c != "\n" and (ord(c) < 32 or 127 <= ord(c) < 160)]


def main():
    tmp = tempfile.mkdtemp(prefix="integration-run-")
    try:
        proj, home, bindir = (os.path.join(tmp, n) for n in ("proj", "home", "bin"))
        counter, pidfile = os.path.join(tmp, "counter"), os.path.join(tmp, "child")
        for d in (os.path.join(proj, "solo-sdd", "changes"), home, bindir):
            os.makedirs(d)
        with open(os.path.join(bindir, "solo-sdd"), "w") as f:
            f.write("#!/bin/sh\nPYTHONPATH=%s exec %s -m solo_sdd \"$@\"\n" % (ROOT, sys.executable))
        os.chmod(os.path.join(bindir, "solo-sdd"), 0o755)
        env = {"PATH": bindir + ":/usr/bin:/bin", "HOME": home, "LANG": "C.UTF-8"}
        integ = os.path.join(proj, "solo-sdd", "integrations", "marker-check")
        cfg = os.path.join(proj, "solo-sdd", "config")

        def put(path, text):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(text)

        def git(*args):
            return subprocess.run(["git", "-c", "user.name=stand", "-c", "user.email=stand@example.com", "-c",
                                   "commit.gpgsign=false", *args], cwd=proj, env=env, capture_output=True, text=True,
                                  stdin=subprocess.DEVNULL, check=True).stdout

        def sdd(*args):
            start = time.monotonic()
            p = subprocess.run(["solo-sdd", *args], cwd=proj, env=env, capture_output=True, text=True, timeout=120,
                               stdin=subprocess.DEVNULL, errors="surrogateescape")
            return p.returncode, p.stdout + p.stderr, time.monotonic() - start

        starts = lambda: len(open(counter).read().splitlines()) if os.path.exists(counter) else 0
        records = lambda: sorted(p for p in glob.glob(os.path.join(home, ".local/share/solo-sdd/checks/*/*.json"))
                                 if not p.endswith("commands.json"))
        call = ("check", "--point", "checks", "--changed")

        put(os.path.join(proj, "README.md"), "readme\n")
        put(os.path.join(integ, "integration"), MARKER)
        put(os.path.join(integ, "check.sh"), "echo x >> %s\n%s" % (counter, FORBID))
        git("init", "-q", "-b", "main")
        git("add", "-A")
        git("commit", "-q", "-m", "base")

        code, out, _ = sdd("check", "--point", "checks")
        step("1 nothing enabled", (code, out) == (0, "no integrations enabled\n"), "exit %d: %s" % (code, out))

        put(cfg, "integrations: marker-check\n")
        put(os.path.join(proj, "app.txt"), "FORBIDDEN\n")
        status = git("status", "--porcelain")
        code, out, _ = sdd(*call)
        lines = out.splitlines()
        step("2 gate fails", code == 1 and lines[:1] == ["command marker-check: %s" % COMMAND]
             and lines[1:] == ["FAIL marker-check: marker in app.txt"] and len(records()) == 1
             and git("status", "--porcelain") == status, "exit %d, %d record(s): %s" % (code, len(records()), out))

        code, out2, _ = sdd(*call)
        tree = os.path.basename(records()[0])[:-5] if records() else "?"
        step("3 reused", code == 1 and out2 == "FAIL marker-check: marker in app.txt\nreused %s\n" % tree
             and starts() == 1, "exit %d, %d start(s): %s" % (code, starts(), out2))

        put(os.path.join(proj, "app.txt"), "fine\n")
        code, out, _ = sdd(*call)
        step("4 marker removed", code == 0 and out == "PASS marker-check: no marker\n" and len(records()) == 2,
             "exit %d, %d record(s): %s" % (code, len(records()), out))

        put(os.path.join(integ, "integration"), MARKER + "requires: no-such-tool\nmissing: warn\n")
        code, out, _ = sdd(*call)
        code2, again, _ = sdd(*call)
        want = "SKIP marker-check: no-such-tool not found"
        step("5 missing tool", (code, code2) == (0, 0) and out.splitlines()[-1:] == [want]
             and again.splitlines() == [want], "exit %d, %d: %s / %s" % (code, code2, out, again))

        put(os.path.join(integ, "integration"), MARKER + "timeout: 2\n")
        put(os.path.join(integ, "check.sh"), "printf '\\033[31mred\\033[0m \\377 byte\\n'\nsleep 30 &\n"
            "echo $! > %s\nsleep 30\n" % pidfile)
        code, out, took = sdd(*call)
        pid = int(open(pidfile).read())
        gone = False
        for _ in range(20):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                gone = True
                break
            time.sleep(0.1)
        rec = json.load(open(max(records(), key=os.path.getmtime)))["points"]["checks"]["lines"]
        step("6 timeout", code == 1 and "FAIL marker-check: timeout 2s" in out.splitlines() and took < 8
             and not controls(out) and not controls("\n".join(rec)) and gone,
             "exit %d in %.1f s, child %s, recorded %r: %s" % (code, took, "gone" if gone else "running", rec, out))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("integration-run: %d of %d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
