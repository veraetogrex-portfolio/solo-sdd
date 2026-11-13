#!/usr/bin/env python3
"""Live Scenario of release-ci, without GitHub: the release text, the changelog checks, the Lint step, pinned actions.

A. scripts/release_check.py --notes v<version> on this tree prints the CHANGELOG.md section; --notes v0.3.0 exits 1.
B. The Changelog test on a copy whose versions say 0.3.0 fails naming 0.3.0.
C. The release check on that copy refuses 0.3.0 with "fail changelog" before building.
D. The run: line of the Lint step of test.yml, on a copy: silent and code 0 as is; an unused import in
   solo_sdd/cli.py gives code 1 and names the file and the line.
E. WorkflowPermissions of tests/test_release.py: every uses: pinned by hash, contents: write only in github-release.
F. The release check of release.yml on a committed copy: v<version> builds and passes, v0.3.0 fails at the version
   (F is reported as not run when python -m build or npm is missing).

Usage: python3 tests/stands/release-ci.py (from the repository root, with hypothesis and pyflakes==3.4.0 installed)
The last line is "total: N of M"; code 0 only if every scenario matched. The stand creates and removes its temporary
folder itself."""
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(ROOT, "scripts", "release_check.py")
GITENV = dict(os.environ, GIT_AUTHOR_NAME="stand", GIT_AUTHOR_EMAIL="s@s", GIT_COMMITTER_NAME="stand",
              GIT_COMMITTER_EMAIL="s@s")
results = []


def run(args, cwd=None):
    return subprocess.run(args, cwd=cwd or tempfile.gettempdir(), capture_output=True, text=True,
                          stdin=subprocess.DEVNULL)


def report(name, ok, detail):
    results.append(ok)
    print(f"{'ok' if ok else 'FAIL'} {name}: {detail}")


def version():
    with open(os.path.join(ROOT, "solo_sdd", "__init__.py"), encoding="utf-8") as f:
        return re.search(r'^__version__\s*=\s*"([^"]*)"', f.read(), re.M).group(1)


def copy_tracked(dest, commit=False):
    """The committed tree plus files not yet committed (not ignored), optionally as one commit of a new repository."""
    files = run(["git", "-C", ROOT, "ls-files", "-z", "--cached", "--others", "--exclude-standard"]).stdout
    for rel in filter(None, files.split("\0")):
        src = os.path.join(ROOT, rel)
        if os.path.isfile(src) and not os.path.islink(src):
            os.makedirs(os.path.dirname(os.path.join(dest, rel)), exist_ok=True)
            shutil.copy2(src, os.path.join(dest, rel))
    if commit:
        for args in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "tree"]):
            subprocess.run(["git", "-C", dest] + args, check=True, env=GITENV, capture_output=True)


def set_version(root, new):
    for rel, pattern, repl in (("package.json", r'"version": "[^"]*"', f'"version": "{new}"'),
                               ("solo_sdd/__init__.py", r'__version__ = "[^"]*"', f'__version__ = "{new}"')):
        path = os.path.join(root, rel)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        with open(path, "w", encoding="utf-8") as f:
            f.write(re.sub(pattern, repl, text, count=1))


def lint_command():
    with open(os.path.join(ROOT, ".github", "workflows", "test.yml"), encoding="utf-8") as f:
        m = re.search(r"- name: Lint\n\s+run: (.+)\n", f.read())
    return m.group(1) if m else None


def main():
    v = version()
    r = run([sys.executable, SCRIPT, "--notes", f"v{v}"])
    lines = r.stdout.splitlines()
    report(f"A notes v{v}", r.returncode == 0 and "- release-ci" in lines and "- registry-release" in lines
           and not any(line.startswith("## ") for line in lines), f"code {r.returncode}, {len(lines)} lines")
    r = run([sys.executable, SCRIPT, "--notes", "v0.3.0"])
    report("A notes v0.3.0", r.returncode == 1 and "0.3.0" in r.stdout, f"code {r.returncode}: {r.stdout.strip()}")

    with tempfile.TemporaryDirectory() as tmp:
        bumped = os.path.join(tmp, "bumped")
        copy_tracked(bumped)
        set_version(bumped, "0.3.0")
        r = run([sys.executable, os.path.join(bumped, "tests", "test_release.py"),
                 "Changelog.test_repository_changelog"])
        named = re.search(r"no section ## 0\.3\.0", r.stdout + r.stderr)
        report("B changelog test on 0.3.0", r.returncode == 1 and bool(named),
               f"code {r.returncode}: {named.group(0) if named else (r.stdout + r.stderr)[-200:]}")

        out = os.path.join(tmp, "dist-bumped")
        r = run([sys.executable, os.path.join(bumped, "scripts", "release_check.py"), "v0.3.0", "--out", out])
        report("C release check on 0.3.0", r.returncode == 1 and r.stdout.startswith("fail changelog")
               and "0.3.0" in r.stdout and not os.path.exists(out), f"code {r.returncode}: {r.stdout.strip()}")

        cmd = lint_command()
        lint = os.path.join(tmp, "lint")
        copy_tracked(lint)
        if cmd is None or importlib.util.find_spec("pyflakes") is None:
            report("D lint step", False, "no Lint step in test.yml" if cmd is None else "pyflakes is not installed")
        else:
            clean = run(["sh", "-c", cmd], cwd=lint)
            cli = os.path.join(lint, "solo_sdd", "cli.py")
            with open(cli, encoding="utf-8") as f:
                text = f.read()
            with open(cli, "w", encoding="utf-8") as f:
                f.write("import zipimport\n" + text)
            broken = run(["sh", "-c", cmd], cwd=lint)
            report("D lint step as is", clean.returncode == 0 and not (clean.stdout + clean.stderr).strip(),
                   f"`{cmd}` code {clean.returncode}, output {len(clean.stdout + clean.stderr)} chars")
            report("D lint step with an unused import", broken.returncode == 1
                   and "solo_sdd/cli.py:1:" in broken.stdout and "imported but unused" in broken.stdout,
                   f"code {broken.returncode}: {broken.stdout.strip()}")

        r = run([sys.executable, os.path.join(ROOT, "tests", "test_release.py"), "WorkflowPermissions"])
        report("E pinned actions and write access", r.returncode == 0,
               (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "no output")

        if importlib.util.find_spec("build") is None or shutil.which("npm") is None:
            report("F release check of release.yml", False, "not run: python -m build or npm is missing")
        else:
            committed = os.path.join(tmp, "committed")
            copy_tracked(committed, commit=True)
            good = run([sys.executable, os.path.join(committed, "scripts", "release_check.py"), f"v{v}",
                        "--out", os.path.join(tmp, "dist")])
            bad = run([sys.executable, os.path.join(committed, "scripts", "release_check.py"), "v0.3.0",
                       "--out", os.path.join(tmp, "dist-bad")])
            last = good.stdout.strip().splitlines()[-1].split(":")[0] if good.stdout.strip() else good.stderr[-200:]
            report(f"F release check v{v}", good.returncode == 0 and last.startswith(f"ok release v{v}"),
                   f"code {good.returncode}: {last}")
            report("F release check v0.3.0", bad.returncode == 1 and "fail version" in bad.stdout
                   and "0.3.0" in bad.stdout and v in bad.stdout, f"code {bad.returncode}: {bad.stdout.strip()}")

    print(f"total: {sum(results)} of {len(results)}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
