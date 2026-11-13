#!/usr/bin/python3
"""Live scenario of change rules-size, steps 1-2, on the doctor of this checkout and the owner's real Codex setup.

Step 1: `doctor` in this checkout and in every folder given as an argument prints a
`rules-size` line whose total and per-file bytes equal `wc -c` of the listed files. Step 2: a temporary git
repository whose AGENTS.md passes the limit gives `fail rules-size:` and exit 1; shortened below 80% it gives
`ok` (the global file is outside the budget). Reads the real $CODEX_HOME, writes only to a temporary folder it removes; the last line is the summary.
"""
import os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
from solo_sdd import doctor  # noqa: E402

PY = "/usr/bin/python3"
checks = []


def check(name, ok, detail=""):
    checks.append(ok)
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else "\n" + detail))


def run_doctor(cwd):
    env = dict(os.environ, PYTHONPATH=ROOT)
    p = subprocess.run([PY, "-m", "solo_sdd", "doctor"], cwd=cwd, env=env, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL)
    line = next((ln for ln in p.stdout.splitlines() if " rules-size: " in ln), "")
    return p.returncode, line


def matches_wc(line):
    m = re.match(r"\w+ rules-size: (\d+) of \d+ bytes; (?:Codex drops[^;]*; )?(.*?)(?:; global (.*) outside the budget)?"
                 r"(?:; config\.toml.*)?$", line)
    if not m:
        return False
    files = [] if m.group(2) == "no project instructions" else [part.rsplit(" ", 1) for part in m.group(2).split(", ")]
    wc = lambda path: int(subprocess.run(["wc", "-c", path], capture_output=True, text=True).stdout.split()[0])
    sizes = [wc(path) for path, _ in files]
    glob_ok = not m.group(3) or wc(m.group(3).rsplit(" ", 1)[0]) == int(m.group(3).rsplit(" ", 1)[1])
    return sizes == [int(size) for _, size in files] and sum(sizes) == int(m.group(1)) and glob_ok


def main():
    for folder in (ROOT, *sys.argv[1:]):
        _, line = run_doctor(folder)
        print(line)
        check(f"step 1 {os.path.basename(folder)}: rules-size totals equal wc -c", matches_wc(line), line)

    home = os.environ.get("CODEX_HOME") or os.path.expanduser("~/.codex")
    limit = doctor._codex_config(home)[0]
    tmp = tempfile.mkdtemp(prefix="rules-size-stand-")
    try:
        subprocess.run(["git", "init", "-q", tmp], check=True)
        agents = os.path.join(tmp, "AGENTS.md")
        with open(agents, "w") as f:
            f.write("x" * (limit + 1000))
        code, line = run_doctor(tmp)
        print(line, f"(exit {code})")
        check("step 2: padded past the limit -> fail rules-size, exit 1",
              line.startswith("fail rules-size:") and code == 1 and matches_wc(line), line)
        with open(agents, "w") as f:
            f.write("x" * max(1, limit * 3 // 4))
        _, line = run_doctor(tmp)
        print(line)
        check("step 2: shortened below 80% -> ok rules-size", line.startswith("ok rules-size:") and matches_wc(line), line)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("rules-size stand: %d of %d checks passed" % (sum(checks), len(checks)))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
