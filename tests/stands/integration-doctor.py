#!/usr/bin/python3
"""Live scenario of change integration-doctor, steps 1-5: `solo-sdd doctor` and the SessionStart hook on a temporary
git project.

A temporary git project with a solo-sdd/ tree and a temporary HOME; PATH is a stand bin folder with a `solo-sdd`
command running the package of this tree with this interpreter, then /usr/bin and /bin. The project holds the
fictional marker-check with the command ./check.sh at the project root. `solo-sdd install` lays the copies out in
the temporary HOME first, so the exit code of `doctor` comes from its integration rows. Step 6 of the scenario (the whole suite) is
the suite command itself, not run here. Run from the repository root: python3 tests/stands/integration-doctor.py.
The temporary folder is removed; the last line is the summary."""
import datetime, json, os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
FILE = "solo-sdd/integrations/marker-check/integration"
LINES = ["name: marker-check", "about: refuses a marker line", "points: checks", "command: ./check.sh"]
passed, total = 0, 0


def step(name, good, detail):
    global passed, total
    total += 1
    passed += bool(good)
    print("%s %s: %s" % ("ok" if good else "FAIL", name, detail.strip().replace("\n", " | ")))


def main():
    tmp = tempfile.mkdtemp(prefix="integration-doctor-")
    try:
        proj, home, bindir = (os.path.join(tmp, n) for n in ("proj", "home", "bin"))
        for d in (os.path.join(proj, "solo-sdd", "changes"), home, bindir):
            os.makedirs(d)
        with open(os.path.join(bindir, "solo-sdd"), "w") as f:
            f.write("#!/bin/sh\nPYTHONPATH=%s exec %s -m solo_sdd \"$@\"\n" % (ROOT, sys.executable))
        os.chmod(os.path.join(bindir, "solo-sdd"), 0o755)
        env = {"PATH": bindir + ":/usr/bin:/bin", "HOME": home, "LANG": "C.UTF-8"}

        def put(rel, text, mode=None):
            path = os.path.join(proj, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(text)
            if mode:
                os.chmod(path, mode)

        def sdd(*args):
            p = subprocess.run(["solo-sdd", *args], cwd=proj, env=env, capture_output=True, text=True, timeout=120,
                               stdin=subprocess.DEVNULL)
            return p.returncode, p.stdout + p.stderr

        def rows(out, prefix):
            return [ln for ln in out.splitlines() if ln.split(":")[0].split(" ", 1)[-1].startswith(prefix)]

        def context():
            p = subprocess.run(["/usr/bin/python3", str(ROOT / "global" / "work_hooks.py"), "context"], env=env,
                               input=json.dumps({"cwd": proj, "source": "startup"}), capture_output=True, text=True,
                               timeout=60)
            text = json.loads(p.stdout)["hookSpecificOutput"]["additionalContext"] if p.stdout.strip() else ""
            return [ln for ln in text.splitlines() if ln.startswith("integration errors")], "### git" in text

        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=proj, env=env, check=True, stdin=subprocess.DEVNULL)
        put("check.sh", "#!/bin/sh\necho no marker\n", 0o755)

        code, out = sdd("install")
        step("0 install into the temporary home", code == 0, "exit %d" % code)
        _, out = sdd("doctor")
        found = rows(out, "integration")
        step("1 nothing enabled", found == ["ok integrations: none enabled"], "; ".join(found) or out)

        put(FILE, "\n".join(LINES + ["requires: sh"]) + "\n")
        put("solo-sdd/config", "integrations: marker-check\n")
        code, run_out = sdd("check", "--point", "checks")
        doctor_code, out = sdd("doctor")
        found = rows(out, "integration")
        want = ("ok integration marker-check: project, points checks, requires sh found, last run PASS %s, "
                "command ./check.sh" % datetime.date.today().isoformat())
        other_fails = [ln for ln in out.splitlines() if ln.startswith("fail ")]
        step("2 a project integration that ran", code == 0 and doctor_code == 0 and found == [want],
             "check exit %d, doctor exit %d; %s" % (code, doctor_code, "; ".join(found + other_fails) or out + run_out))

        put(FILE, "\n".join(LINES + ["requires: no-such-tool"]) + "\n")
        _, out = sdd("doctor")
        found = rows(out, "integration")
        step("3 a missing tool", len(found) == 1 and found[0].startswith("warn integration marker-check: ")
             and "requires no-such-tool missing" in found[0], "; ".join(found) or out)

        bad = LINES[:2] + ["nosuchkey: 1"] + LINES[3:]
        put(FILE, "\n".join(bad) + "\n")
        code, out = sdd("doctor")
        found = rows(out, "integration")
        fails = [ln for ln in out.splitlines() if ln.startswith("fail ") and ln not in found]
        step("4 a broken description", code == 1 and len(found) == 1
             and found[0].startswith("fail integration marker-check: %s:3: unknown key nosuchkey" % FILE)
             and fails == [], "exit %d; %s" % (code, "; ".join(found + fails) or out))

        lines, rest = context()
        step("5a the context names the error", rest and len(lines) == 1
             and lines[0].startswith("integration errors: %s:3: unknown key nosuchkey" % FILE), "; ".join(lines))
        put(FILE, "\n".join(LINES) + "\n")
        lines, rest = context()
        step("5b no line once fixed", rest and lines == [], "; ".join(lines) or "no integration errors line")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("integration-doctor: %d of %d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
