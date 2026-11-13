#!/usr/bin/python3
"""Live scenario of change product-identity, step 2 Fallback: the README quick start runs as written.

Takes the first bash block of the README "Quick start" section and runs its lines in one shell with a temporary
HOME, PATH=<shim>:/usr/bin:/bin and an empty git repository at the folder the block `cd`s into. The `pip install`
line is the only one not run: a `solo-sdd` shim runs this tree's package instead (no network, nothing installed
outside the temporary folder). Then checks: the quick start heading is before line 40, every slash command the
section names is a deployed skill, `solo-sdd validate --all` passes in the project. The temporary folder is removed;
the last line is the summary.
"""
import os, pathlib, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
results = []


def step(name, good, detail=""):
    results.append(bool(good))
    print("%s %s%s" % ("ok  " if good else "FAIL", name, (": " + detail.strip().replace("\n", " | ")) if detail else ""))


def main():
    lines = (ROOT / "README.md").read_text(encoding="utf-8").splitlines()
    at = lines.index("## Quick start")
    section = "\n".join(lines[at:]).split("\n## ", 1)[0]
    block = section.split("```bash\n", 1)[1].split("```", 1)[0].splitlines()
    step("quick start heading at line %d" % (at + 1), at + 1 < 40)
    tmp = tempfile.mkdtemp(prefix="readme-quickstart-")
    try:
        home, shim = os.path.join(tmp, "home"), os.path.join(tmp, "bin")
        os.makedirs(home)
        os.makedirs(shim)
        with open(os.path.join(shim, "solo-sdd"), "w") as f:
            f.write('#!/bin/sh\nPYTHONPATH="%s" exec "%s" -m solo_sdd "$@"\n' % (ROOT, sys.executable))
        os.chmod(os.path.join(shim, "solo-sdd"), 0o755)
        env = {"HOME": home, "PATH": shim + ":/usr/bin:/bin", "LANG": "C.UTF-8"}
        run = [l for l in block if l.strip() and not l.startswith("pip install ")]
        step("install line replaced by the shim", len(run) == len(block) - 1, "%d lines run" % len(run))
        cd = next((l.split(None, 1)[1] for l in run if l.startswith("cd ")), None)
        project = os.path.expanduser(cd.replace("~", home, 1)) if cd else home
        os.makedirs(project)
        subprocess.run(["git", "init", "-q", "-b", "main"], cwd=project, env=env, check=True, stdin=subprocess.DEVNULL)
        p = subprocess.run(["/bin/sh", "-e", "-c", "\n".join(run)], cwd=home, env=env, capture_output=True,
                           text=True, timeout=300, stdin=subprocess.DEVNULL)
        out = p.stdout + p.stderr
        step("block runs: %s" % " / ".join(run), p.returncode == 0 and "next: /project-init" in out,
             "exit %d, %s" % (p.returncode, out.strip().splitlines()[-1] if out.strip() else "no output"))
        skills = sorted(set(re.findall(r"`/([a-z][a-z-]*)", section)))
        missing = [s for s in skills if not os.path.isfile(os.path.join(home, ".agents", "skills", s, "SKILL.md"))]
        step("slash commands deployed: %s" % ", ".join(skills), skills and not missing, ("missing " + ", ".join(missing)) if missing else "")
        v = subprocess.run([os.path.join(shim, "solo-sdd"), "validate", "--all"], cwd=project, env=env,
                           capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
        step("validate --all in the project", v.returncode == 0, (v.stdout + v.stderr).strip())
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("readme-quickstart: %d ok, %d FAIL" % (results.count(True), results.count(False)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
