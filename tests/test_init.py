#!/usr/bin/env python3
"""solo-sdd init: поддельный openspec в PATH, временные репозитории."""
import contextlib, io, os, stat, subprocess, sys, tempfile, unittest
from unittest import mock

from hypothesis import given, settings, strategies as st

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from solo_sdd import cli, init  # noqa: E402

FAKE = """#!/bin/sh
case "$1" in
init) echo init >> "$FAKE_LOG"; [ -n "$FAKE_FAIL" ] && { echo "boom: tools" >&2; exit 3; }; mkdir -p openspec; printf 'schema: spec-driven\\n' > openspec/config.yaml ;;
schemas) [ -z "$FAKE_NOSOLO" ] && echo "  solo (user override)" || echo "  spec-driven" ;;
esac
"""
FILES = ("openspec/config.yaml", "openspec/analyze.md", "docs/waiting.md")


def snapshot(root):
    out = {}
    for d, dirs, names in os.walk(root):
        dirs[:] = [x for x in dirs if x != ".git"]
        for n in names:
            p = os.path.join(d, n)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root)] = f.read()
    return out


class Env:
    def __init__(self, fake=True, git=True):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.proj, self.log = os.path.join(t, "proj"), os.path.join(t, "log")
        os.makedirs(self.proj)
        if git:
            os.mkdir(os.path.join(self.proj, ".git"))
        bindir = os.path.join(t, "bin")
        os.mkdir(bindir)
        if fake:
            exe = os.path.join(bindir, "openspec")
            with open(exe, "w") as f:
                f.write(FAKE)
            os.chmod(exe, os.stat(exe).st_mode | stat.S_IXUSR)
        self.patch = mock.patch.dict(os.environ, {"PATH": bindir + os.pathsep + "/usr/bin:/bin", "FAKE_LOG": self.log})

    def __enter__(self):
        self.patch.start()
        return self

    def __exit__(self, *a):
        self.patch.stop()
        self.tmp.cleanup()

    def write(self, rel, text):
        p = os.path.join(self.proj, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write(text)

    def init(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = init.run(self.proj)
        return code, buf.getvalue()

    def calls(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as f:
            return f.read().split()


class InitTest(unittest.TestCase):
    def test_new_project(self):
        with Env() as e:
            code, out = e.init()
            self.assertEqual(code, 0)
            files = snapshot(e.proj)
            self.assertIn(b"schema: solo", files["openspec/config.yaml"])
            self.assertIn("openspec/analyze.md", files)
            self.assertIn("docs/waiting.md", files)
            self.assertEqual(e.calls(), ["init"])
            self.assertEqual(out.splitlines()[-1], "дальше: /project-init в Claude Code или Codex")

    def test_own_config(self):
        with Env() as e:
            e.write("openspec/config.yaml", "schema: spec-driven\ncontext: своё\n")
            code, out = e.init()
            self.assertEqual(code, 0)
            self.assertEqual(snapshot(e.proj)["openspec/config.yaml"], b"schema: spec-driven\ncontext: \xd1\x81\xd0\xb2\xd0\xbe\xd1\x91\n")
            self.assertIn("config.yaml уже есть: schema spec-driven", out)
            self.assertEqual(e.calls(), [])

    def test_not_repo(self):
        with Env(git=False) as e:
            code, out = e.init()
            self.assertEqual(code, 1)
            self.assertIn("не git-репозиторий: git init", out)
            self.assertEqual(snapshot(e.proj), {})

    def test_repeat(self):
        with Env() as e:
            e.init()
            before = snapshot(e.proj)
            code, out = e.init()
            self.assertEqual(code, 0)
            self.assertEqual(snapshot(e.proj), before)
            self.assertEqual(e.calls(), ["init"])
            self.assertNotIn("создано", out)

    def test_no_openspec(self):
        with Env(fake=False) as e:
            code, out = e.init()
            self.assertEqual(code, 1)
            self.assertIn(init.INSTALL, out.splitlines())
            self.assertEqual(snapshot(e.proj), {})

    def test_openspec_init_fails(self):
        with Env() as e, mock.patch.dict(os.environ, {"FAKE_FAIL": "1"}):
            code, out = e.init()
            self.assertEqual(code, 1)
            self.assertIn("boom: tools", out)
            self.assertNotIn("дальше", out)
            self.assertEqual(snapshot(e.proj), {})

    def test_no_solo_schema_warns(self):
        with Env() as e, mock.patch.dict(os.environ, {"FAKE_NOSOLO": "1"}):
            code, out = e.init()
            self.assertEqual(code, 0)
            self.assertIn("warn: схемы solo нет в openspec schemas", out.splitlines())

    def test_openspec_dir_without_config(self):
        with Env() as e:
            e.write("openspec/specs/.keep", "")
            code, out = e.init()
            self.assertEqual(code, 0)
            self.assertEqual(e.calls(), [])
            with open(os.path.join(e.proj, "openspec/config.yaml"), encoding="utf-8") as f:
                self.assertRegex(f.read(), r"(?m)^schema: solo$")

    def test_cli_arguments(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["init", "a", "b"]), 2)

    @settings(max_examples=25, deadline=None)
    @given(st.dictionaries(st.sampled_from(FILES), st.text()))
    def test_project_init_idempotent_property(self, existing):
        with Env() as e:
            for rel, text in existing.items():
                e.write(rel, text)
            before = snapshot(e.proj)
            self.assertEqual(e.init()[0], 0)
            first = snapshot(e.proj)
            for rel, data in before.items():
                self.assertEqual(first[rel], data, rel)
            self.assertEqual(e.init()[0], 0)
            self.assertEqual(snapshot(e.proj), first)


if __name__ == "__main__":
    unittest.main()
