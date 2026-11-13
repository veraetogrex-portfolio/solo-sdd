#!/usr/bin/env python3
"""Stand of change purge-keeps-integrations: `uninstall --purge` keeps the owner's integration.

On a temporary home the stand creates and removes (never the real one):
  1. install: the last line is `all laid out`;
  2. an owner integration integrations/demo/integration and a checks cache in ~/.local/share/solo-sdd/;
  3. uninstall --purge: exit 0, a `kept` line names ~/.local/share/solo-sdd/integrations;
  4. what is left under ~/.local/share is only solo-sdd/integrations/demo/integration;
  5. the integration still reads `name: demo`.
"""
import os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
checks = []


def check(name, good, detail=""):
    checks.append(good)
    print(("ok   " if good else "FAIL ") + name + ("" if good or not detail else ": " + detail.strip()[-600:]))


def main():
    tmp = tempfile.mkdtemp()
    try:
        home = os.path.join(tmp, "home")
        os.makedirs(os.path.join(home, ".claude"))
        env = dict(os.environ, HOME=home, PYTHONPATH=ROOT)

        def run(*args):
            p = subprocess.run([sys.executable, "-m", "solo_sdd", *args], cwd=tmp, env=env, capture_output=True,
                               text=True, stdin=subprocess.DEVNULL, timeout=300)
            return p.returncode, p.stdout + p.stderr

        code, out = run("install")
        check("1 install: all laid out", code == 0 and out.strip().splitlines()[-1:] == ["all laid out"], out)
        share = os.path.join(home, ".local/share")
        data = os.path.join(share, "solo-sdd")
        owner = os.path.join(data, "integrations/demo/integration")
        os.makedirs(os.path.dirname(owner))
        os.makedirs(os.path.join(data, "checks"))
        with open(owner, "w") as f:
            f.write("name: demo\n")
        check("2 owner integration and checks cache created", os.path.isfile(owner))
        code, out = run("uninstall", "--purge")
        kept = [" ".join(line.split()[:2]) for line in out.splitlines() if line.startswith("kept")]
        check("3 uninstall --purge: exit 0, kept ~/.local/share/solo-sdd/integrations",
              code == 0 and kept == ["kept ~/.local/share/solo-sdd/integrations"], out)
        left = sorted(os.path.relpath(os.path.join(d, n), share) for d, _, names in os.walk(share) for n in names)
        check("4 only solo-sdd/integrations/demo/integration left", left == ["solo-sdd/integrations/demo/integration"],
              repr(left))
        text = open(owner).read() if os.path.isfile(owner) else None
        check("5 integration reads name: demo", text == "name: demo\n", repr(text))
    finally:
        shutil.rmtree(tmp, True)
    print(f"{sum(checks)} of {len(checks)} checks passed")
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
