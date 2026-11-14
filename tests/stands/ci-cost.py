#!/usr/bin/env python3
"""Live stand of the change ci-cost: what the two workflows run for each event, read without a YAML library.

1. test.yml, by the line reader of tests/test_release.py: the operating systems and the runner tier per event, the
   concurrency group with cancel-in-progress: true, Lint before the runner steps.
2. release.yml: its runner step is the release tier.
3. python3 tests/test_release.py exits with code 0.

Usage: python3 tests/stands/ci-cost.py (from the repository root). Without Hypothesis it reruns itself with the
first interpreter that has it: sys.executable, then /usr/bin/python3.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def has_hypothesis(py):
    return subprocess.run([py, "-c", "import hypothesis"], capture_output=True, stdin=subprocess.DEVNULL).returncode == 0


if not has_hypothesis(sys.executable):
    if os.path.exists("/usr/bin/python3") and has_hypothesis("/usr/bin/python3"):
        os.execv("/usr/bin/python3", ["/usr/bin/python3", os.path.abspath(__file__)])
    print("FAIL no interpreter with Hypothesis: sys.executable, /usr/bin/python3")
    sys.exit(1)

sys.path.insert(0, os.path.join(ROOT, "tests"))
import test_release as t  # noqa: E402

EXPECTED = {("push", "refs/heads/main"): (["ubuntu-latest"], ["slow"]),
            ("pull_request", "refs/pull/1/merge"): (["ubuntu-latest"], ["slow"]),
            ("push", "refs/tags/v0.3.0"): (["macos-latest"], ["release"]),
            ("workflow_dispatch", "refs/heads/main"): (["ubuntu-latest", "macos-latest"], ["release"])}
failed = []


def report(name, ok, detail):
    print("%s %s: %s" % ("ok" if ok else "FAIL", name, detail))
    if not ok:
        failed.append(name)


def read(*rel):
    with open(os.path.join(ROOT, *rel), encoding="utf-8") as f:
        return f.read()


def main():
    test, release = read(".github", "workflows", "test.yml"), read(".github", "workflows", "release.yml")
    expr = [line.split("os: ", 1)[1] for line in test.splitlines() if line.strip().startswith("os: ${{")]
    block = t.jobs(test)["test"]
    for (event, ref), (want_os, want_tier) in EXPECTED.items():
        got_os = sorted(t.evaluate(expr[0], event, ref)) if expr else None
        got_tier = t.runner_tiers(block, event, ref)
        report("1 test.yml %s %s" % (event, ref), got_os == sorted(want_os) and got_tier == want_tier,
               "os %s, tier %s" % (got_os, got_tier))
    head = test.split("\njobs:\n", 1)[0]
    conc = "concurrency:\n  group: ${{ github.workflow }}-${{ github.ref }}\n  cancel-in-progress: true\n"
    report("1 test.yml concurrency", conc in head, "group ${{ github.workflow }}-${{ github.ref }}, "
           "cancel-in-progress: %s" % ("true" if conc in head else "missing"))
    steps = t.steps(block)
    names = [s["name"] for s in steps]
    runners = [i for i, s in enumerate(steps) if "tests/run.py" in s["run"]]
    report("1 test.yml Lint first", "Lint" in names and runners and names.index("Lint") < min(runners),
           "steps %s" % names)
    tiers = t.runner_tiers(t.jobs(release)["check"], "push", "refs/tags/v0.3.0")
    report("2 release.yml tier", tiers == ["release"], "tier %s" % tiers)
    r = subprocess.run([sys.executable, os.path.join(ROOT, "tests", "test_release.py")], capture_output=True,
                       text=True, cwd=ROOT, stdin=subprocess.DEVNULL)
    tail = (r.stderr.strip().splitlines() or [""])[-1]
    report("3 tests/test_release.py", r.returncode == 0, "code %d, %s" % (r.returncode, tail))
    if r.returncode:
        print(r.stderr[-3000:])
    print("SUMMARY: all steps passed" if not failed else "SUMMARY: failed: %s" % ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
