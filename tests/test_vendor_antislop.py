#!/usr/bin/env python3
"""Закреплённая копия anti-slop: раскладка, VERSION, ссылки R-XX, Hard Gate, contrast-check."""
import glob, json, os, re, shutil, subprocess, sys, tempfile, unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENDOR = os.path.join("vendor", "antislop")
CONTRAST = os.path.join(REPO, VENDOR, "skills", "antislop-human", "contrast-check.py")


def no_dups(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("повтор ключа %r" % k)
        out[k] = v
    return out


def load_targets(text=None):
    if text is None:
        with open(os.path.join(REPO, "targets.json")) as f:
            text = f.read()
    return json.loads(text, object_pairs_hook=no_dups)


def core_rules(root):
    with open(os.path.join(root, VENDOR, "antislop.md")) as f:
        return set(re.findall(r"^#### (R-\d\d)\b", f.read(), re.M))


def dangling_rules(root):
    """Сообщения о R-XX из skills/*/SKILL.md, которых нет в ядре."""
    known, bad = core_rules(root), []
    for path in sorted(glob.glob(os.path.join(root, "skills", "*", "SKILL.md"))):
        with open(path) as f:
            text = f.read()
        rel = os.path.relpath(path, root)
        for r in sorted(set(re.findall(r"R-\d\d", text)) - known):
            bad.append("%s в %s нет в ядре" % (r, rel))
    return bad


class VendorTest(unittest.TestCase):
    def test_duplicate_key_fails(self):
        with self.assertRaisesRegex(ValueError, "'a'"):
            load_targets('{"x": {"a": 1, "a": 2}}')

    def test_targets_have_no_duplicates(self):
        load_targets()

    def test_layout_covers_copy(self):
        t = load_targets()
        roots = [t["roots"][n] for n in t["skills"]["ui-check"]]
        base = os.path.join(REPO, VENDOR)
        for dp, _, names in os.walk(base):
            for n in names:
                if n in ("README.md", "VERSION") or n.startswith("LICENSE"):
                    continue
                key = os.path.relpath(os.path.join(dp, n), REPO)
                self.assertIn(key, t["files"], key)
                for r in roots:
                    pre = "%s/ui-check/antislop/" % r
                    self.assertTrue(any(p.startswith(pre) for p in t["files"][key]), "%s: нет пути в %s" % (key, pre))
        for key in t["files"]:
            if key.startswith("vendor/"):
                self.assertTrue(os.path.isfile(os.path.join(REPO, key)), key)

    def test_version(self):
        with open(os.path.join(REPO, VENDOR, "VERSION")) as f:
            lines = f.read().split("\n")
        self.assertRegex(lines[0], r"^v\d+\.\d+\.\d+$")
        self.assertRegex(lines[1], r"^[0-9a-f]{40}$")

    def test_rule_refs_exist(self):
        self.assertEqual(dangling_rules(REPO), [])

    def test_dangling_rule_detected(self):
        tmp = tempfile.mkdtemp()
        try:
            shutil.copytree(os.path.join(REPO, "skills"), os.path.join(tmp, "skills"))
            shutil.copytree(os.path.join(REPO, "vendor"), os.path.join(tmp, "vendor"))
            os.makedirs(os.path.join(tmp, "skills", "ui-check"), exist_ok=True)
            with open(os.path.join(tmp, "skills", "ui-check", "SKILL.md"), "a") as f:
                f.write("\nСм. R-41.\n")
            self.assertIn("R-41 в skills/ui-check/SKILL.md нет в ядре", dangling_rules(tmp))
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
