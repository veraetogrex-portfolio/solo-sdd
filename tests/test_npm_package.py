#!/usr/bin/env python3
"""npm-обёртка: те же вывод и код, что у python3 -m solo_sdd; состав npm pack и версии."""
import json, os, re, shutil, subprocess, sys, tempfile, unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WRAPPER = os.path.join(REPO, "bin", "solo-sdd.js")
NODE = shutil.which("node")
NPM = shutil.which("npm")
MUST = ("bin/", "solo_sdd/", "skills/", "global/", "schema/", "templates/",
        "targets.json", "ALGORITHM.md", "LICENSE", "README.md")
NEVER = ("tests/", "openspec/", ".github/", "docs/")


def versions(root):
    """Версии из package.json, pyproject.toml (или hatch: solo_sdd/__init__.py) и solo_sdd.__version__."""
    package = json.load(open(os.path.join(root, "package.json")))["version"]
    init = re.search(r'__version__\s*=\s*"([^"]+)"', open(os.path.join(root, "solo_sdd", "__init__.py")).read()).group(1)
    pyproject = open(os.path.join(root, "pyproject.toml")).read()
    static = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M)
    if static:
        py = static.group(1)
    else:
        assert 'path = "solo_sdd/__init__.py"' in pyproject, "pyproject.toml: нет version и нет hatch path"
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
        """Сценарий «Разошлась версия»: этот же файл на копии с 0.1.1 в package.json — код 1 и обе версии."""
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        for d in ("solo_sdd", "tests"):
            os.makedirs(os.path.join(tmp, d))
        for f in ("pyproject.toml", "solo_sdd/__init__.py", "tests/test_npm_package.py"):
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


@unittest.skipIf(NODE is None, "node нет в PATH: обёртка не проверена")
class Wrapper(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, True)

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
        """В текущей папке лежит чужой solo_sdd: обёртка всё равно запускает пакет рядом с собой."""
        other = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, other, True)
        os.makedirs(os.path.join(other, "solo_sdd"))
        for name in ("__init__.py", "__main__.py"):
            with open(os.path.join(other, "solo_sdd", name), "w") as f:
                f.write("print('чужой'); raise SystemExit(7)\n")
        p = subprocess.run([NODE, WRAPPER, "status"], cwd=other, capture_output=True, text=True,
                           env=dict(os.environ, HOME=self.home, SOLO_SDD_PYTHON=sys.executable))
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertTrue(p.stdout.startswith(f"источник: {REPO} "), p.stdout.splitlines()[0])

    def test_order_and_pythonpath(self):
        """python3 старый — берётся python; ему передаются корень пакета в PYTHONPATH и аргументы."""
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
        self.assertEqual((code, out.splitlines()[-1]), (5, "ARGS=status"), "SOLO_SDD_PYTHON важнее python3 из PATH")

    def test_signal_passed(self):
        fake = os.path.join(self.home, "py")
        with open(fake, "w") as f:
            f.write('#!/bin/sh\ncase "$2" in *version_info*) echo 3.12; exit 0;; esac\nkill -TERM $$\n')
        os.chmod(fake, 0o755)
        code, _, _ = run([NODE, WRAPPER, "status"], self.home, extra={"SOLO_SDD_PYTHON": fake})
        self.assertEqual(code, -15)

    def test_no_python(self):
        code, out, err = run([NODE, WRAPPER, "status"], self.home, path="/nonexistent", extra={"SOLO_SDD_PYTHON": ""})
        self.assertEqual((code, out, err), (1, "solo-sdd: нужен Python 3.9+ (найден: нет)\n", ""))

    def test_old_python_named(self):
        fake = os.path.join(self.home, "bin")
        os.makedirs(fake)
        for name in ("python3", "python"):
            with open(os.path.join(fake, name), "w") as f:
                f.write("#!/bin/sh\necho 3.8\n")
            os.chmod(os.path.join(fake, name), 0o755)
        code, out, _ = run([NODE, WRAPPER, "status"], self.home, path=fake, extra={"SOLO_SDD_PYTHON": ""})
        self.assertEqual((code, out), (1, "solo-sdd: нужен Python 3.9+ (найден: 3.8, 3.8)\n"))


@unittest.skipIf(NPM is None, "npm нет в PATH: состав npm pack не проверен")
class Contents(unittest.TestCase):
    def test_pack(self):
        p = subprocess.run([NPM, "pack", "--dry-run", "--json", "--ignore-scripts"], cwd=REPO,
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 0, p.stderr)
        files = [f["path"] for f in json.loads(p.stdout)[0]["files"]]
        for need in MUST:
            self.assertTrue(any(f == need or f.startswith(need) for f in files), need)
        for bad in NEVER:
            self.assertEqual([f for f in files if f.startswith(bad)], [], bad)
        if shutil.which("git") and os.path.exists(os.path.join(REPO, ".git")):
            ignored = subprocess.run(["git", "check-ignore", "--stdin"], cwd=REPO, input="\n".join(files),
                                     capture_output=True, text=True).stdout.split()
            self.assertEqual(ignored, [], "в пакет попали файлы из .gitignore")


if __name__ == "__main__":
    unittest.main()
