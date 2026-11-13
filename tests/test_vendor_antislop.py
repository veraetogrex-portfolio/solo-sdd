#!/usr/bin/env python3
"""Pinned copy of anti-slop, the bundled integration antislop: deployment for ui-check and copy-check, VERSION, its
integration description, R-XX links, Hard Gate, contrast-check."""
import glob, json, os, re, shutil, subprocess, sys, tempfile, unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from solo_sdd import integrations, layout  # noqa: E402
from solo_sdd.providers import PROVIDERS  # noqa: E402
VENDOR = os.path.join("integrations", "antislop")
CONTRAST = os.path.join(REPO, VENDOR, "skills", "antislop-human", "contrast-check.py")
COPYWRITING = os.path.join(VENDOR, "skills", "antislop-copywriting", "SKILL.md")
# which skills read a copy file; a file not in the list means ui-check only
READERS = {
    os.path.join(VENDOR, "antislop.md"): ("ui-check", "copy-check"),
    COPYWRITING: ("copy-check",),
}


def no_dups(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("duplicate key %r" % k)
        out[k] = v
    return out


def load_targets(text=None):
    if text is None:
        with open(os.path.join(REPO, "targets.json")) as f:
            text = f.read()
    return json.loads(text, object_pairs_hook=no_dups)


def places():
    """Copy file -> the paths from ~ the layout puts it at for every agent: the skill entries expanded."""
    out = {}
    for rel, _, target, _ in layout.pairs(list(PROVIDERS), True):
        out.setdefault(rel, []).append(layout.short(target))
    return out


def core_rules(root):
    with open(os.path.join(root, VENDOR, "antislop.md")) as f:
        return set(re.findall(r"^#### (R-\d\d)\b", f.read(), re.M))


def dangling_rules(root):
    """Mentions of R-XX from skills/*/SKILL.md that are not in the core."""
    known, bad = core_rules(root), []
    for path in sorted(glob.glob(os.path.join(root, "skills", "*", "SKILL.md"))):
        with open(path) as f:
            text = f.read()
        rel = os.path.relpath(path, root)
        for r in sorted(set(re.findall(r"R-\d\d", text)) - known):
            bad.append("%s in %s is not in the core" % (r, rel))
    return bad


class VendorTest(unittest.TestCase):
    def test_duplicate_key_fails(self):
        with self.assertRaisesRegex(ValueError, "'a'"):
            load_targets('{"x": {"a": 1, "a": 2}}')

    def test_targets_have_no_duplicates(self):
        load_targets()

    def test_layout_covers_copy(self):
        t = load_targets()
        base = os.path.join(REPO, VENDOR)
        for dp, _, names in os.walk(base):
            for n in names:
                if n in ("README.md", "VERSION", "integration") or n.startswith("LICENSE"):
                    self.assertNotIn(os.path.relpath(os.path.join(dp, n), REPO), t["files"])
                    continue
                key = os.path.relpath(os.path.join(dp, n), REPO)
                self.assertIn(key, t["files"], key)
                laid = places()[key]
                for skill in READERS.get(key, ("ui-check",)):
                    for r in (PROVIDERS[x]["skills"] for x in t["skills"][skill] if PROVIDERS[x]["skills"]):  # unprobed: no root
                        pre = "%s/%s/antislop/" % (r, skill)
                        self.assertTrue(any(p.startswith(pre) for p in laid), "%s: no path in %s" % (key, pre))
        for key in t["files"]:
            if key.startswith("integrations/"):
                self.assertTrue(os.path.isfile(os.path.join(REPO, key)), key)

    def test_copy_check_layout(self):
        t = load_targets()
        self.assertEqual(sorted(t["skills"]["copy-check"]), sorted(t["skills"]["ui-check"]))
        core = places()[os.path.join(VENDOR, "antislop.md")]
        copywriting = places()[COPYWRITING]
        roots = [PROVIDERS[x]["skills"] for x in t["skills"]["copy-check"] if PROVIDERS[x]["skills"]]  # unprobed: no root
        for r in roots:
            self.assertIn("%s/copy-check/antislop/core.md" % r, core)
            self.assertIn("%s/copy-check/antislop/copywriting.md" % r, copywriting)
        self.assertEqual(len(copywriting), len(roots))

    def test_copywriting_copy(self):
        with open(os.path.join(REPO, COPYWRITING), encoding="utf-8") as f:
            text = f.read()
        self.assertTrue(text.startswith("---\nname: antislop-copywriting\n"))
        for part in ("## What NOT to flag", "## Signs of human writing", "## Voice calibration", "## Draft, audit, final"):
            self.assertIn(part, text)
        refs = set(re.findall(r"R-\d\d", text))
        self.assertEqual(refs - core_rules(REPO), set())

    def test_copy_check_rule_refs(self):
        with open(os.path.join(REPO, "skills", "copy-check", "SKILL.md"), encoding="utf-8") as f:
            refs = set(re.findall(r"R-\d\d", f.read()))
        self.assertLessEqual({"R-02", "R-15", "R-16", "R-17"}, refs)
        self.assertEqual(refs - core_rules(REPO), set())

    def test_version(self):
        with open(os.path.join(REPO, VENDOR, "VERSION")) as f:
            lines = f.read().split("\n")
        self.assertRegex(lines[0], r"^v\d+\.\d+\.\d+$")
        self.assertRegex(lines[1], r"^[0-9a-f]{40}$")

    def test_pinned_antislop_rules_integration_description(self):
        """Requirement: Pinned antislop rules: the copy carries its integration description, whose material is the core."""
        base = os.path.join(REPO, VENDOR)
        fields = integrations.read_integration(base, "antislop", os.path.join(VENDOR, "integration"))
        self.assertEqual((fields["points"], fields["tags"], fields["material"]), (["review"], ["ui", "copy"], "antislop.md"))
        self.assertEqual(sorted(n for n in os.listdir(base) if n.startswith("LICENSE")), ["LICENSE"])
        self.assertEqual([n for _, _, names in os.walk(os.path.join(REPO, "vendor")) for n in names], [])  # moved whole

    def test_rule_refs_exist(self):
        self.assertEqual(dangling_rules(REPO), [])

    def test_dangling_rule_detected(self):
        tmp = tempfile.mkdtemp()
        try:
            shutil.copytree(os.path.join(REPO, "skills"), os.path.join(tmp, "skills"))
            shutil.copytree(os.path.join(REPO, "integrations"), os.path.join(tmp, "integrations"))
            os.makedirs(os.path.join(tmp, "skills", "ui-check"), exist_ok=True)
            with open(os.path.join(tmp, "skills", "ui-check", "SKILL.md"), "a") as f:
                f.write("\nSee R-41.\n")
            self.assertIn("R-41 in skills/ui-check/SKILL.md is not in the core", dangling_rules(tmp))
        finally:
            shutil.rmtree(tmp)

    def test_hard_gate_has_19_lines(self):
        with open(os.path.join(REPO, VENDOR, "antislop.md")) as f:
            text = f.read()
        m = re.search(r"^### Block 1: Hard Gate.*?$(.*?)(?=^### )", text, re.M | re.S)
        self.assertTrue(m)
        self.assertEqual(len(re.findall(r"^- \[ \]", m.group(1), re.M)), 19)

    def run_contrast(self, *args):
        return subprocess.run([sys.executable, CONTRAST, *args], stdin=subprocess.DEVNULL,
                              capture_output=True, text=True)

    def test_contrast_selftest(self):
        self.assertEqual(self.run_contrast("--selftest").returncode, 0)

    def test_contrast_ratio(self):
        r = self.run_contrast("#999999", "#FFFFFF")
        self.assertIn("ratio: 2.85:1", r.stdout)


if __name__ == "__main__":
    unittest.main()
