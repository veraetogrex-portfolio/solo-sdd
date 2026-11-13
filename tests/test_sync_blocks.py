#!/usr/bin/env python3
"""scripts/sync_blocks.py: block copies from one source, broken markers refused; on temporary copies of the tree."""
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from hypothesis import assume, given, settings as hsettings, strategies as st

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SCRIPT = os.path.join(REPO, "scripts", "sync_blocks.py")
spec = importlib.util.spec_from_file_location("sync_blocks", SCRIPT)
sync_blocks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_blocks)

MARKER = re.compile(r"^# [a-z0-9-]+:(begin|end)\r?$", re.M)


def tree_copy(dest):
    """The scanned folders and the script, without caches: the script finds its root from its own path."""
    for d in ("solo_sdd", "global", "scripts"):
        shutil.copytree(os.path.join(REPO, d), os.path.join(dest, d), ignore=shutil.ignore_patterns("__pycache__"))


def snapshot(root):
    out = {}
    for d in ("solo_sdd", "global"):
        for base, _, files in os.walk(os.path.join(root, d)):
            for f in files:
                with open(os.path.join(base, f), "rb") as fh:
                    out[os.path.relpath(os.path.join(base, f), root)] = fh.read()
    return out


def read(root, rel):
    with open(os.path.join(root, rel), encoding="utf-8", newline="") as f:
        return f.read()


def write(root, rel, text):
    os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
    with open(os.path.join(root, rel), "w", encoding="utf-8", newline="") as f:
        f.write(text)


def block(text, name):
    return text[text.index("# %s:begin\n" % name):text.index("# %s:end" % name)]


class Tree(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="sync-blocks-")
        self.addCleanup(shutil.rmtree, self.root)
        tree_copy(self.root)

    def run_script(self, *args):
        r = subprocess.run([sys.executable, os.path.join(self.root, "scripts", "sync_blocks.py"), *args],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        return r.returncode, r.stdout + r.stderr


class BlockCopiesFromOneSource(Tree):
    """Requirement: Block copies from one source."""

    def test_block_copies_from_one_source_an_edit_in_the_source(self):
        before = snapshot(self.root)
        src = read(self.root, "solo_sdd/settings.py")
        edited = src.replace("# settings:end", "NEW_KEY = 1  # a new key\n# settings:end")
        write(self.root, "solo_sdd/settings.py", edited)
        code, out = self.run_script()
        self.assertEqual(code, 0, out)
        copies = ("global/sdd_dispatch_plan.py", "global/work_hooks.py", "global/sdd_worktree.py", "global/sdd_pr.py")
        after = snapshot(self.root)
        for rel in copies:
            text = read(self.root, rel)
            self.assertEqual(block(text, "settings"), block(edited, "settings"), rel)
            old = before[rel].decode()
            self.assertEqual(text.replace(block(text, "settings"), ""), old.replace(block(old, "settings"), ""), rel)
            self.assertIn(rel, out)
        changed = {k for k in after if after[k] != before[k]}
        self.assertEqual(changed, set(copies) | {"solo_sdd/settings.py"})

    def test_block_copies_from_one_source_a_stale_copy(self):
        text = read(self.root, "global/sdd_pr.py")
        write(self.root, "global/sdd_pr.py", text.replace("# settings:begin\n", "# settings:begin\nOLD = 0\n"))
        before = snapshot(self.root)
        code, out = self.run_script("--check")
        self.assertEqual(code, 1, out)
        self.assertIn("global/sdd_pr.py: settings", out)
        self.assertEqual(snapshot(self.root), before)

    def test_block_copies_from_one_source_idempotent(self):
        text = read(self.root, "global/process-guard.py")
        write(self.root, "global/process-guard.py", text.replace("# shell:begin\n", "# shell:begin\nX = 1\n"))
        self.assertEqual(self.run_script()[0], 0)
        once = snapshot(self.root)
        code, out = self.run_script()
        self.assertEqual((code, out), (0, ""))
        self.assertEqual(snapshot(self.root), once)
        self.assertEqual(self.run_script("--check"), (0, ""))

    def test_block_copies_from_one_source_the_tree_is_in_sync(self):
        self.assertEqual(self.run_script("--check"), (0, ""))

    def test_block_copies_from_one_source_a_usage_error(self):
        code, out = self.run_script("--chek")
        self.assertEqual(code, 2, out)


class BrokenMarkersRefused(Tree):
    """Requirement: Broken markers refused."""

    def broken(self, rel, old, new, name, check=False):
        write(self.root, rel, read(self.root, rel).replace(old, new, 1))
        before = snapshot(self.root)
        code, out = self.run_script(*(["--check"] if check else []))
        self.assertEqual(code, 1, out)
        self.assertIn("%s: %s" % (rel, name), out)
        self.assertEqual(snapshot(self.root), before)

    def test_broken_markers_refused_a_missing_end_marker(self):
        # a stale copy elsewhere too: the refusal comes before any write
        text = read(self.root, "global/sdd_worktree.py")
        write(self.root, "global/sdd_worktree.py", text.replace("# settings:begin\n", "# settings:begin\nOLD = 0\n"))
        for check in (False, True):
            with self.subTest(check=check):
                self.broken("global/sdd_pr.py", "# settings:end\n", "", "settings", check)

    def test_broken_markers_refused_another_end_names_the_open_block(self):
        self.broken("global/sdd_pr.py", "# settings:end\n", "# keywords:end\n", "settings")

    def test_broken_markers_refused_an_end_without_begin(self):
        self.broken("global/sdd_pr.py", "# keywords:begin\n", "", "keywords")

    def test_broken_markers_refused_a_block_twice(self):
        self.broken("global/sdd_eval.py", "\n\ndef archived(", "\n\n# process-root:begin\n# process-root:end\n\n\ndef archived(",
                    "process-root")

    def test_broken_markers_refused_a_name_without_source(self):
        self.broken("global/sdd_eval.py", "\n\ndef archived(", "\n\n# no-such:begin\n# no-such:end\n\n\ndef archived(",
                    "no-such")

    def test_broken_markers_refused_a_source_without_its_block(self):
        text = read(self.root, "solo_sdd/keywords.py")
        write(self.root, "solo_sdd/keywords.py", text.replace("# keywords:end\n", "", 1))
        self.broken("solo_sdd/keywords.py", "# keywords:begin\n", "", "keywords")


class UnreadInputRefused(Tree):
    """Requirements: Block copies from one source (every .py file is read) and Broken markers refused: an entry the
    script cannot read the way Python does is refused, never skipped."""

    def refused(self, needle):
        text = read(self.root, "global/sdd_pr.py")
        write(self.root, "global/sdd_pr.py", text.replace("# settings:begin\n", "# settings:begin\nOLD = 0\n"))
        before = snapshot(self.root)
        for args in ((), ("--check",)):
            code, out = self.run_script(*args)
            self.assertEqual(code, 1, out)
            self.assertIn(needle, out)
        self.assertEqual(snapshot(self.root), before)

    def test_a_lone_cr_file(self):
        write(self.root, "global/cr.py", "x = 1\r# settings:begin\rA = 1\r# settings:end\r")
        self.refused("global/cr.py holds a line break that is a lone CR")

    def test_a_linked_folder(self):
        os.symlink(os.path.join(self.root, "scripts"), os.path.join(self.root, "global", "linked"))
        self.refused("global/linked is a link")

    def test_a_linked_file(self):
        os.symlink(os.path.join(self.root, "scripts", "sync_blocks.py"), os.path.join(self.root, "global", "linked.py"))
        self.refused("global/linked.py is a link")

    def test_a_crlf_file_is_read(self):
        write(self.root, "global/crlf.py", "x = 1\r\n# settings:begin\r\nA = 1\r\n# settings:end\r\ny = 2\r\n")
        code, out = self.run_script("--check")
        self.assertEqual(code, 1, out)
        self.assertIn("global/crlf.py: settings: differs", out)
        self.assertEqual(self.run_script()[0], 0)
        text = read(self.root, "global/crlf.py")
        self.assertTrue(text.startswith("x = 1\r\n# settings:begin\r\n") and text.endswith("# settings:end\r\ny = 2\r\n"))
        inner = text[text.index("# settings:begin\r\n") + 18:text.index("# settings:end")]
        self.assertEqual(inner, block(read(self.root, "solo_sdd/settings.py"), "settings")[len("# settings:begin\n"):])

    def test_a_missing_folder(self):
        for d in ("global", "solo_sdd"):
            shutil.rmtree(os.path.join(self.root, d))
            for args in ((), ("--check",)):
                code, out = self.run_script(*args)
                self.assertEqual(code, 1, out)
                self.assertIn("%s/ is missing" % d, out)

    @unittest.skipIf(os.geteuid() == 0, "root lists any folder")
    def test_an_unlistable_folder(self):
        sub = os.path.join(self.root, "global", "closed")
        os.mkdir(sub)
        os.chmod(sub, 0)
        self.addCleanup(os.chmod, sub, 0o700)
        self.refused("closed")

    @unittest.skipIf(os.geteuid() == 0, "root writes any file")
    def test_a_read_only_copy_stops_every_write(self):
        for rel in ("global/sdd_pr.py", "global/sdd_worktree.py"):
            text = read(self.root, rel)
            write(self.root, rel, text.replace("# settings:begin\n", "# settings:begin\nOLD = 0\n"))
        os.chmod(os.path.join(self.root, "global/sdd_worktree.py"), 0o444)
        before = snapshot(self.root)
        code, out = self.run_script()
        self.assertEqual(code, 1, out)
        self.assertIn("global/sdd_worktree.py: cannot be written", out)
        self.assertNotIn("copied from", out)
        self.assertEqual(snapshot(self.root), before)


# Property tests on a synthetic tree: one source, one copy, one file without markers.
# a lone CR is refused input (UnreadInputRefused), so the generated text holds no CR
CHARS = st.characters(blacklist_characters="\r", blacklist_categories=("Cs",))
LINE = st.text(st.characters(blacklist_characters="\r\n", blacklist_categories=("Cs",)), max_size=12).filter(
    lambda s: not MARKER.search(s))
LINES = st.lists(LINE, max_size=4).map(lambda ls: "".join(x + "\n" for x in ls))
TAIL = st.one_of(st.just(""), LINE, LINES)
KNOWN = "settings"


def run_sync(root, check=False):
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        code = sync_blocks.sync(root, check)
    return code, buf.getvalue()


def files(root):
    return {rel: read(root, rel) for rel in ("solo_sdd/settings.py", "global/copy.py", "global/plain.py")
            if os.path.exists(os.path.join(root, rel))}


class Properties(unittest.TestCase):

    @hsettings(max_examples=150, deadline=None, database=None)
    @given(LINES, LINES, LINES, TAIL, LINES, TAIL, st.booleans(), st.text(CHARS, max_size=20).filter(lambda s: not MARKER.search(s)))
    def test_block_copies_from_one_source_property(self, body, old, pre1, post1, pre2, post2, no_newline, plain):
        end1 = "# %s:end" % KNOWN + ("" if no_newline and not post1 else "\n")
        source = pre1 + "# %s:begin\n" % KNOWN + body + end1 + (post1 if end1.endswith("\n") else "")
        copy = pre2 + "# %s:begin\n" % KNOWN + old + "# %s:end\n" % KNOWN + post2
        with tempfile.TemporaryDirectory() as root:
            write(root, "solo_sdd/settings.py", source)
            write(root, "global/copy.py", copy)
            write(root, "global/plain.py", plain)
            code, out = run_sync(root, check=True)
            self.assertEqual(code, 0 if body == old else 1, out)
            self.assertEqual(files(root)["global/copy.py"], copy)
            self.assertEqual(run_sync(root)[0], 0)
            got = files(root)
            self.assertEqual(got["global/copy.py"], pre2 + "# %s:begin\n" % KNOWN + body + "# %s:end\n" % KNOWN + post2)
            self.assertEqual(got["solo_sdd/settings.py"], source)
            self.assertEqual(got["global/plain.py"], plain)
            self.assertEqual(run_sync(root), (0, ""))
            self.assertEqual(files(root), got)
            self.assertEqual(run_sync(root, check=True), (0, ""))

    @hsettings(max_examples=150, deadline=None, database=None)
    @given(st.lists(st.tuples(st.sampled_from([KNOWN, "zz-other"]), st.sampled_from(["begin", "end"]), LINES),
                    min_size=1, max_size=5), st.booleans())
    def test_broken_markers_refused_property(self, marks, in_source):
        # the oracle: with one known name, the only valid set is its begin then its end
        assume([(n, k) for n, k, _ in marks] != [(KNOWN, "begin"), (KNOWN, "end")])
        broken = "".join("# %s:%s\n%s" % (n, k, text) for n, k, text in marks)
        source = "x = 1\n# %s:begin\nA = 1\n# %s:end\n" % (KNOWN, KNOWN)
        copy = "# %s:begin\nA = 0\n# %s:end\n" % (KNOWN, KNOWN)
        with tempfile.TemporaryDirectory() as root:
            write(root, "solo_sdd/settings.py", broken if in_source else source)
            write(root, "global/copy.py", copy)
            write(root, "global/plain.py", copy if in_source else broken)
            before = files(root)
            for check in (False, True):
                code, out = run_sync(root, check)
                self.assertEqual(code, 1, out)
                self.assertIn("solo_sdd/settings.py" if in_source else "global/plain.py", out)
                self.assertEqual(files(root), before)


if __name__ == "__main__":
    unittest.main()
