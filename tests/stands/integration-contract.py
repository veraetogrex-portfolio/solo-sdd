#!/usr/bin/python3
"""Live scenario of change integration-contract, steps 1-6: `solo-sdd integrations` and `solo-sdd config`.

A temporary git project with a solo-sdd/ tree and a temporary HOME; PATH is a stand bin folder with a `solo-sdd`
command running the package of this tree, then /usr/bin and /bin. The project holds the fictional marker-check, the
home the fictional dup-scan. Step 7 of the scenario (the whole suite) is the suite command itself, not run here.
Run from the repository root: python3 tests/stands/integration-contract.py. The temporary folder is removed; the
last line is the summary."""
import os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
MARKER = ('name: marker-check\nabout: refuses a marker line\npoints: checks\n'
          'command: sh "$SOLO_SDD_INTEGRATION_DIR/check.sh"\n')
DUP = "name: dup-scan\nabout: finds copied code\npoints: checks\ncommand: dup-scan .\n"
COMMENT = "# stand settings: keep this line\n"
passed, total = 0, 0


def step(name, good, detail):
    global passed, total
    total += 1
    passed += bool(good)
    print("%s %s: %s" % ("ok" if good else "FAIL", name, detail.strip().replace("\n", " | ")))


def main():
    tmp = tempfile.mkdtemp(prefix="integration-contract-")
    try:
        proj, home, bindir = (os.path.join(tmp, n) for n in ("proj", "home", "bin"))
        for d in (os.path.join(proj, "solo-sdd", "changes"), home, bindir):
            os.makedirs(d)
        with open(os.path.join(bindir, "solo-sdd"), "w") as f:
            f.write("#!/bin/sh\nPYTHONPATH=%s exec %s -m solo_sdd \"$@\"\n" % (ROOT, PY))
        os.chmod(os.path.join(bindir, "solo-sdd"), 0o755)
        env = {"PATH": bindir + ":/usr/bin:/bin", "HOME": home, "LANG": "C.UTF-8"}

        def sdd(*args):
            p = subprocess.run(["solo-sdd", *args], cwd=proj, env=env, capture_output=True, text=True, timeout=120,
                               stdin=subprocess.DEVNULL)
            return p.returncode, p.stdout + p.stderr

        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=proj, env=env, check=True, stdin=subprocess.DEVNULL)
        for base, name, text in ((os.path.join(proj, "solo-sdd", "integrations"), "marker-check", MARKER),
                                 (os.path.join(home, ".local", "share", "solo-sdd", "integrations"), "dup-scan", DUP)):
            os.makedirs(os.path.join(base, name))
            with open(os.path.join(base, name, "integration"), "w") as f:
                f.write(text)
        cfg = os.path.join(proj, "solo-sdd", "config")
        with open(cfg, "w") as f:
            f.write(COMMENT + "dispatch.limit: 2\n")
        read = lambda: open(cfg, "rb").read()
        lines = lambda out: [" ".join(ln.split()) for ln in out.splitlines()]

        code, out = sdd("integrations", "list")
        got = lines(out)
        step("1 list", code == 0 and any(l.startswith("marker-check project disabled checks") for l in got)
             and any(l.startswith("dup-scan owner disabled checks") for l in got), "exit %d: %s" % (code, out))

        code, out = sdd("integrations", "enable", "dup-scan")
        value = sdd("config", "get", "integrations")[1].splitlines()[0]
        step("2 enable owner", code == 0 and value == "dup-scan" and read().startswith(COMMENT.encode()),
             "exit %d, config get: %s, comment kept: %s" % (code, value, read().startswith(COMMENT.encode())))

        sdd("integrations", "enable", "marker-check")
        before = read()
        code, out = sdd("integrations", "enable", "marker-check")
        step("3 enable twice", code == 0 and b"\nintegrations: dup-scan, marker-check\n" in before and read() == before,
             "exit %d, file unchanged: %s, %s" % (code, read() == before, out))

        code, out = sdd("integrations", "disable", "dup-scan")
        listing = sdd("integrations", "list")[1]
        step("4 disable", code == 0 and b"\nintegrations: marker-check\n" in read()
             and any(l.startswith("dup-scan owner disabled") for l in lines(listing)), out + listing)

        broken = MARKER.splitlines(True)
        broken[2] = "colour: red\n"
        with open(os.path.join(proj, "solo-sdd", "integrations", "marker-check", "integration"), "w") as f:
            f.write("".join(broken))
        code, out = sdd("integrations", "list")
        before = read()
        code2, out2 = sdd("integrations", "enable", "marker-check")
        step("5 broken", code == 1 and "dup-scan owner" in out and "solo-sdd/integrations/marker-check/integration:3"
             in out and "colour" in out and code2 == 1 and read() == before,
             "list exit %d: %s; enable exit %d: %s" % (code, out, code2, out2))

        sdd("config", "set", "integrations", "no-such")
        code, out = sdd("integrations", "list")
        code2, out2 = sdd("integrations", "disable", "no-such")
        value = sdd("config", "get", "integrations")[1].splitlines()[0]
        step("6 stale name", code == 1 and "no-such" in out and code2 == 0 and value == "",
             "list exit %d: %s; disable exit %d: %s; integrations: %r" % (code, out, code2, out2, value))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("integration-contract: %d of %d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
