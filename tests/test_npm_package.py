#!/usr/bin/env python3
"""npm wrapper: the same output and code as python3 -m solo_sdd; npm pack contents and versions."""
import json, os, re, shutil, subprocess, sys, tempfile, unittest
import marks

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WRAPPER = os.path.join(REPO, "bin", "solo-sdd.js")
NODE = shutil.which("node")
NPM = shutil.which("npm")
MUST = ("bin/", "solo_sdd/", "skills/", "global/", "templates/", "integrations/",
        "targets.json", "ALGORITHM.md", "LICENSE", "README.md")
NEVER = ("tests/", "solo-sdd/", ".github/", "docs/")


def versions(root):
    """Versions from package.json, pyproject.toml (or hatch: solo_sdd/__init__.py) and solo_sdd.__version__."""
    package = json.load(open(os.path.join(root, "package.json")))["version"]
    init = re.search(r'__version__\s*=\s*"([^"]+)"', open(os.path.join(root, "solo_sdd", "__init__.py")).read()).group(1)
    pyproject = open(os.path.join(root, "pyproject.toml")).read()
    static = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    if static:
        py = static.group(1)
    else:
        assert 'path = "solo_sdd/__init__.py"' in pyproject, "pyproject.toml: no version and no hatch path"
        py = init
    return {"package.json": package, "pyproject.toml": py, "solo_sdd/__init__.py": init}


def run(args, home, path=None, extra=None):
    env = dict(os.environ, HOME=home)
    env.pop("PYTHONPATH", None)
    env.pop("SOLO_SDD_PYTHON", None)
    if path is not None:
        env["PATH"] = path
    env.update(extra or {})
    p = subprocess.run(args, cwd=REPO, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout, p.stderr


class Versions(unittest.TestCase):
    def test_same_version(self):
        v = versions(REPO)
        self.assertEqual(len(set(v.values())), 1, v)

    def test_mismatch_named(self):
        """Scenario "Version mismatch": this same file on a copy with 0.1.1 in package.json gives code 1 and both versions."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        for d in ("solo_sdd", "tests"):
            os.makedirs(os.path.join(tmp, d))
        for f in ("pyproject.toml", "solo_sdd/__init__.py", "tests/test_npm_package.py", "tests/marks.py"):
            shutil.copy(os.path.join(REPO, f), os.path.join(tmp, f))
        with open(os.path.join(REPO, "package.json")) as f:
            pkg = json.load(f)
        pkg["version"] = "0.1.1"
        with open(os.path.join(tmp, "package.json"), "w") as f:
            json.dump(pkg, f)
        p = subprocess.run([sys.executable, os.path.join(tmp, "tests", "test_npm_package.py"), "Versions.test_same_version"],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertIn("'package.json': '0.1.1'", p.stderr)
        self.assertIn(f"'solo_sdd/__init__.py': '{versions(REPO)['solo_sdd/__init__.py']}'", p.stderr)


@unittest.skipIf(NODE is None, "node not in PATH: the wrapper is not checked")
class Wrapper(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, True)

    @marks.slow
    def test_same_as_python(self):
        for args in (["--version"], ["status"], ["frobnicate"]):
            want = run([sys.executable, "-m", "solo_sdd", *args], self.home)
            got = run([NODE, WRAPPER, *args], self.home, extra={"SOLO_SDD_PYTHON": sys.executable})
            self.assertEqual(got, want, args)
        self.assertEqual(got[0], 2)

    def test_runs_from_other_cwd(self):
        other = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, other, True)
        p = subprocess.run([NODE, WRAPPER, "--version"], cwd=other, capture_output=True, text=True,
                           env=dict(os.environ, HOME=self.home, SOLO_SDD_PYTHON=sys.executable))
        self.assertEqual((p.returncode, p.stdout.strip()), (0, versions(REPO)["solo_sdd/__init__.py"]))

    def test_package_wins_over_cwd(self):
        """A foreign solo_sdd lies in the current folder: the wrapper still runs the package next to itself."""
        other = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, other, True)
        os.makedirs(os.path.join(other, "solo_sdd"))
        for name in ("__init__.py", "__main__.py"):
            with open(os.path.join(other, "solo_sdd", name), "w") as f:
                f.write("print('foreign'); raise SystemExit(7)\n")
        p = subprocess.run([NODE, WRAPPER, "status"], cwd=other, capture_output=True, text=True,
                           env=dict(os.environ, HOME=self.home, SOLO_SDD_PYTHON=sys.executable))
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertTrue(p.stdout.startswith(f"source: {REPO} "), p.stdout.splitlines()[0])

    def test_order_and_pythonpath(self):
        """python3 is old, so python is taken; it gets the package root in PYTHONPATH and the arguments."""
        fake = os.path.join(self.home, "bin")
        os.makedirs(fake)
        scripts = {"python3": "echo 3.8\n",
                   "python": 'case "$1" in -c) case "$2" in *version_info*) echo 3.12; exit 0;; esac;; esac\n'
                             'echo "PYTHONPATH=$PYTHONPATH"; shift 3; echo "ARGS=$*"; exit 5\n'}
        for name, body in scripts.items():
            with open(os.path.join(fake, name), "w") as f:
                f.write("#!/bin/sh\n" + body)
            os.chmod(os.path.join(fake, name), 0o755)
        code, out, _ = run([NODE, WRAPPER, "init", "x y"], self.home, path=fake + ":/usr/bin:/bin",
                           extra={"SOLO_SDD_PYTHON": "", "PYTHONPATH": "/extra"})
        self.assertEqual((code, out), (5, f"PYTHONPATH={REPO}{os.pathsep}/extra\nARGS=init x y\n"))
        code, out, _ = run([NODE, WRAPPER, "status"], self.home, path="/usr/bin:/bin",
                           extra={"SOLO_SDD_PYTHON": os.path.join(fake, "python")})
        self.assertEqual((code, out.splitlines()[-1]), (5, "ARGS=status"), "SOLO_SDD_PYTHON wins over python3 from PATH")

    def test_signal_passed(self):
        fake = os.path.join(self.home, "py")
        with open(fake, "w") as f:
            f.write('#!/bin/sh\ncase "$2" in *version_info*) echo 3.12; exit 0;; esac\nkill -TERM $$\n')
        os.chmod(fake, 0o755)
        code, _, _ = run([NODE, WRAPPER, "status"], self.home, extra={"SOLO_SDD_PYTHON": fake})
        self.assertEqual(code, -15)

    def test_no_python(self):
        code, out, err = run([NODE, WRAPPER, "status"], self.home, path="/nonexistent", extra={"SOLO_SDD_PYTHON": ""})
        self.assertEqual((code, out, err), (1, "solo-sdd: Python 3.9+ needed (found: none)\n", ""))

    def test_old_python_named(self):
        fake = os.path.join(self.home, "bin")
        os.makedirs(fake)
        for name in ("python3", "python"):
            with open(os.path.join(fake, name), "w") as f:
                f.write("#!/bin/sh\necho 3.8\n")
            os.chmod(os.path.join(fake, name), 0o755)
        code, out, _ = run([NODE, WRAPPER, "status"], self.home, path=fake, extra={"SOLO_SDD_PYTHON": ""})
        self.assertEqual((code, out), (1, "solo-sdd: Python 3.9+ needed (found: 3.8, 3.8)\n"))


@marks.release
@unittest.skipIf(NPM is None, "npm not in PATH: npm pack contents not checked")
class Contents(unittest.TestCase):
    def test_pack(self):
        p = subprocess.run([NPM, "pack", "--dry-run", "--json", "--ignore-scripts"], cwd=REPO,
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 0, p.stderr)
        files = [f["path"] for f in json.loads(p.stdout)[0]["files"]]
        for need in MUST:
            self.assertTrue(any(f == need or f.startswith(need) for f in files), need)
        sys.path.insert(0, REPO)
        from solo_sdd import layout, providers
        laid_out = {os.path.relpath(source, REPO) for _, source, _, _ in layout.pairs(providers.ALL)}
        self.assertEqual(sorted(laid_out - set(files)), [], "the package lacks files that install deploys")
        for bad in NEVER:
            self.assertEqual([f for f in files if f.startswith(bad)], [], bad)
        if shutil.which("git") and os.path.exists(os.path.join(REPO, ".git")):
            ignored = subprocess.run(["git", "check-ignore", "--stdin"], cwd=REPO, input="\n".join(files),
                                     capture_output=True, text=True).stdout.split()
            self.assertEqual(ignored, [], "files from .gitignore got into the package")


if __name__ == "__main__":
    unittest.main()
