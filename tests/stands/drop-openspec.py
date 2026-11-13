#!/usr/bin/env python3
"""Stand of change drop-openspec: a wheel of this tree in a fresh venv, a temporary HOME, PATH without openspec.

Steps 1-4 of its Live Scenario: install, init + new + validate, doctor, the old schema copies.
The temporary folder is created and removed here; prints one line per check and the total."""
import glob, hashlib, json, os, shutil, subprocess, sys, tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"{'ok  ' if ok else 'FAIL'} {name}" + (f": {detail}" if detail and not ok else ""))


def run(args, cwd, env):
    p = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=600)
    return p.returncode, p.stdout + p.stderr


def main():
    t = tempfile.mkdtemp(prefix="drop-openspec-")
    try:
        code, out = run([sys.executable, "-m", "pip", "wheel", REPO, "--no-deps", "-q", "-w", os.path.join(t, "dist")], t, None)
        if code:
            check("0 wheel built", False, out[-500:])
            return
        venv = os.path.join(t, "v")
        subprocess.run([sys.executable, "-m", "venv", venv], check=True, stdin=subprocess.DEVNULL)
        code, out = run([os.path.join(venv, "bin", "pip"), "install", "-q", "--no-index", *glob.glob(os.path.join(t, "dist", "*.whl"))], t, None)
        check("0 wheel installed in a fresh venv", code == 0, out[-500:])
        exe = os.path.join(venv, "bin", "solo-sdd")
        path = os.path.join(venv, "bin") + ":/usr/bin:/bin"
        has_openspec = any(os.path.exists(os.path.join(d, "openspec")) for d in path.split(":"))
        check("0 no openspec in PATH", not has_openspec)

        def env(home):
            os.makedirs(home, exist_ok=True)
            return {"HOME": home, "PATH": path, "LANG": "C.UTF-8"}

        home = os.path.join(t, "home")
        code, out = run([exe, "install"], t, env(home))
        check("1 install exit 0, no openspec line", code == 0 and "openspec" not in out.lower(), out[-800:])
        check("1 no ~/.local/bin/openspec-after-update.py",
              not os.path.exists(os.path.join(home, ".local/bin/openspec-after-update.py")))
        check("1 template ~/.local/share/solo-sdd/templates/solo-sdd/project.md",
              os.path.isfile(os.path.join(home, ".local/share/solo-sdd/templates/solo-sdd/project.md")))

        p = os.path.join(t, "p")
        os.makedirs(p)
        run(["git", "init", "-q", p], t, env(home))
        code, out = run([exe, "init"], p, env(home))
        paths = ("solo-sdd/project.md", "solo-sdd/analyze.md", "solo-sdd/specs", "solo-sdd/changes", "docs/waiting.md")
        lines = out.splitlines()
        check("2 init: the five paths, last line next: /project-init",
              code == 0 and all(os.path.exists(os.path.join(p, x)) for x in paths) and lines[-1:] == ["next: /project-init"]
              and len([l for l in lines if l.startswith("created ")]) == 5, out)
        code, out = run([exe, "validate", "--all"], p, env(home))
        check("2 validate --all on the new tree exit 0", code == 0, out)
        code, out = run([exe, "new", "demo"], p, env(home))
        check("2 new demo", code == 0, out)
        code, out = run([exe, "validate", "--all"], p, env(home))
        errors = [l for l in out.splitlines() if ": " in l and not l.endswith(" errors")]
        check("2 validate --all fails only on the template change", code == 1 and errors
              and all(l.startswith("solo-sdd/changes/demo/") for l in errors), out)
        before = run(["find", ".", "-not", "-path", "./.git*"], p, env(home))[1]
        code, out = run([exe, "init"], p, env(home))
        check("2 repeated init prints no created line and changes nothing",
              code == 0 and "created" not in out and run(["find", ".", "-not", "-path", "./.git*"], p, env(home))[1] == before, out)

        code, out = run([exe, "doctor"], p, env(home))
        names = [l.split(":")[0] for l in out.splitlines()]
        check("3 doctor: no openspec or schema line, exit 0",
              code == 0 and not any("openspec" in n or "schema" in n for n in names), out)

        home2 = os.path.join(t, "home2")
        code, out = run([exe, "install"], t, env(home2))
        state_file = os.path.join(home2, ".local/share/solo-sdd/state.json")
        with open(state_file) as f:
            state = json.load(f)
        planted = {"~/.local/bin/openspec-after-update.py": ("old script\n", "old script\n"),
                   "~/.local/bin/test_openspec_after_update.py": ("old test, edited\n", "old test\n")}
        for key, (text, recorded) in planted.items():
            target = os.path.join(home2, key[2:])
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w") as f:
                f.write(text)
            state[key] = hashlib.sha256(recorded.encode()).hexdigest()
        with open(state_file, "w") as f:
            json.dump(state, f)
        job = os.path.join(home2, "Library/LaunchAgents/local.openspec-after-update.plist")
        os.makedirs(os.path.dirname(job))
        with open(job, "w") as f:
            f.write("<plist/>\n")
        code, out = run([exe, "install"], t, env(home2))
        lines = out.splitlines()
        check("4 an unchanged old copy is removed and named",
              not os.path.exists(os.path.join(home2, ".local/bin/openspec-after-update.py"))
              and any(l.startswith("removed") and "openspec-after-update.py" in l for l in lines), out)
        check("4 an edited old copy is kept and named as drift",
              os.path.exists(os.path.join(home2, ".local/bin/test_openspec_after_update.py"))
              and any(l.startswith("kept") and "test_openspec_after_update.py" in l and "drift" in l for l in lines), out)
        check("4 the launchd job file is named and untouched",
              os.path.exists(job) and any("local.openspec-after-update.plist" in l for l in lines), out)
        print("\n".join("  | " + l for l in lines if l.startswith(("removed", "kept", "old job"))))
    finally:
        shutil.rmtree(t, ignore_errors=True)
        print(f"drop-openspec stand: {sum(results)} of {len(results)} passed")


if __name__ == "__main__":
    main()
    sys.exit(0 if results and all(results) else 1)
