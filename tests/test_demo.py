#!/usr/bin/env python3
"""examples/demo: requirements Demo project and Walkthrough runs as written (capability quickstart-demo)."""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import marks

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEMO = os.path.join(REPO, "examples", "demo")
BLOCK_RE = re.compile(r"^```bash\n(.*?)^```", re.M | re.S)


def bash_lines(text):
    """The command lines of the fenced bash blocks, in the order of the file."""
    return [l for block in BLOCK_RE.findall(text) for l in block.splitlines() if l.strip()]


def env_for(home):
    """A temporary HOME with `solo-sdd` on PATH running this repository's package, and a git identity."""
    bin_dir = os.path.join(home, ".bin")
    os.makedirs(bin_dir, exist_ok=True)
    shim = os.path.join(bin_dir, "solo-sdd")
    with open(shim, "w", encoding="utf-8") as f:
        f.write('#!/bin/sh\nexec "%s" -m solo_sdd "$@"\n' % sys.executable)
    os.chmod(shim, 0o755)
    env = dict(os.environ, HOME=home, PATH=bin_dir + os.pathsep + os.environ.get("PATH", ""), PYTHONPATH=REPO)
    for k in ("GIT_AUTHOR", "GIT_COMMITTER"):
        env[k + "_NAME"], env[k + "_EMAIL"] = "Demo", "demo@example.com"
    for k in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        env.pop(k, None)
    return env


def run_walkthrough(text, home, demo=DEMO):
    """Run every bash line of `text` in one shell under `home`; a `git clone` line is replaced by a copy of `demo`
    at the clone target. Returns the CompletedProcess; a failing line is named on stderr as `FAILED: <line>`."""
    script = ["set -e", "trap 'echo \"FAILED: $BASH_COMMAND\" >&2' ERR"]
    for line in bash_lines(text):
        if line.startswith("git clone "):
            target = line.split()[-1]
            target = home + target[1:] if target.startswith("~") else os.path.join(home, target)
            shutil.copytree(demo, os.path.join(target, "examples", "demo"))
            continue
        script.append(line)
    return subprocess.run(["bash", "-c", "\n".join(script)], cwd=home, env=env_for(home), capture_output=True,
                          text=True, stdin=subprocess.DEVNULL, timeout=300)


def lines_with(out, prefix):
    """Lines of `out` that start with `prefix`, whitespace collapsed."""
    return [" ".join(l.split()) for l in out.splitlines() if l.startswith(prefix)]


class DemoProject(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.copy = os.path.join(self.tmp, "demo")
        shutil.copytree(DEMO, self.copy)

    def run_in_copy(self, *cmd):
        return subprocess.run(list(cmd), cwd=self.copy, env=env_for(self.tmp), capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=120)

    def test_the_demo_stays_valid(self):
        r = self.run_in_copy(sys.executable, "-m", "solo_sdd", "validate", "--all")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("0 errors", r.stdout)
        r = self.run_in_copy(sys.executable, "-m", "unittest", "discover", "-s", "tests")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_tree_shape(self):
        tree = os.path.join(self.copy, "solo-sdd")
        self.assertEqual(os.listdir(os.path.join(tree, "specs")), ["tip"])
        archived = [n for n in os.listdir(os.path.join(tree, "changes", "archive")) if not n.startswith(".")]
        self.assertEqual(len(archived), 1, archived)
        self.assertTrue(archived[0].endswith("-tip-calc"), archived)
        r = self.run_in_copy(sys.executable, "-m", "solo_sdd", "list")
        self.assertEqual(lines_with(r.stdout, "split-bill"), ["split-bill 0/4"], r.stdout)
        self.assertTrue(os.path.isfile(os.path.join(self.copy, "WALKTHROUGH.md")))


class WalkthroughRunsAsWritten(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, True)

    @marks.slow
    def test_commands(self):
        with open(os.path.join(DEMO, "WALKTHROUGH.md"), encoding="utf-8") as f:
            text = f.read()
        self.assertTrue(any(l.startswith("git clone ") for l in bash_lines(text)))
        r = run_walkthrough(text, self.home)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(lines_with(r.stdout, "split-bill"), ["split-bill 0/4", "split-bill 0/4"], r.stdout)
        self.assertEqual(lines_with(r.stdout, "0 errors"), ["0 errors", "0 errors"], r.stdout)
        log = subprocess.run(["git", "log", "--format=%s"], cwd=os.path.join(self.home, "solo-sdd-demo"),
                             capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout
        self.assertEqual(log, "demo start\n")

    def test_failing_command_is_named(self):
        text = "x\n\n```bash\ntrue\nfalse\necho after\n```\n"
        r = run_walkthrough(text, self.home)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("FAILED: false", r.stderr)
        self.assertNotIn("after", r.stdout)

    def test_the_readme_link(self):
        with open(os.path.join(REPO, "README.md"), encoding="utf-8") as f:
            quick = f.read().split("## Quick start", 1)[1].split("\n## ", 1)[0]
        # An absolute address to the file (Registry install documented: the link opens from the PyPI and npm pages).
        self.assertIn("(https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/examples/demo/WALKTHROUGH.md)", quick)


if __name__ == "__main__":
    unittest.main()
