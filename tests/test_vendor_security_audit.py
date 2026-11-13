#!/usr/bin/env python3
"""Pinned copy of cloudflare/security-audit-skill, the bundled integration security-audit: VERSION hashes, license,
its integration description, deployment under spec-audit/security/."""
import hashlib, json, os, re, shutil, tempfile, unittest, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)
from solo_sdd import integrations, layout  # noqa: E402
from solo_sdd.providers import PROVIDERS  # noqa: E402
VENDOR = os.path.join("integrations", "security-audit")
NOT_DEPLOYED = ("LICENSE", "README.md", "VERSION", "integration")
OWN = ("VERSION", "integration")  # solo-sdd's own files of the copy: not upstream, not hashed


def copy_files(base):
    rels = (os.path.relpath(os.path.join(d, n), base) for d, _, names in os.walk(base) for n in names)
    return sorted(r for r in rels if r not in OWN)  # only the top-level own files are skipped


def changed_files(root):
    """Vendored files whose sha256 differs from VERSION, files missing from it and files it lists that are gone."""
    base = os.path.join(root, VENDOR)
    with open(os.path.join(base, "VERSION")) as f:
        lines = f.read().splitlines()
    pinned = dict(reversed(line.split("  ", 1)) for line in lines[1:] if line)
    bad = []
    for rel in copy_files(base):
        with open(os.path.join(base, rel), "rb") as f:
            got = hashlib.sha256(f.read()).hexdigest()
        if rel not in pinned:
            bad.append("%s: not in VERSION" % rel)
        elif pinned[rel] != got:
            bad.append("%s: hash differs from VERSION" % rel)
    bad += ["%s: listed in VERSION, missing" % rel for rel in sorted(set(pinned) - set(copy_files(base)))]
    return bad


def places():
    """Copy file -> the paths from ~ the layout puts it at for every agent: the skill entries expanded."""
    out = {}
    for rel, _, target, _ in layout.pairs(list(PROVIDERS), True):
        out.setdefault(rel, []).append(layout.short(target))
    return out


class SecurityAuditCopy(unittest.TestCase):
    def test_version_commit(self):
        with open(os.path.join(REPO, VENDOR, "VERSION")) as f:
            self.assertRegex(f.readline().strip(), r"^c1c8a8c[0-9a-f]{33}$")

    def test_validator_tests_not_vendored(self):
        self.assertEqual([r for r in copy_files(os.path.join(REPO, VENDOR)) if r.endswith(".test.cjs")], [])

    def test_license_is_mit(self):
        with open(os.path.join(REPO, VENDOR, "LICENSE")) as f:
            self.assertIn("MIT License", f.read())

    def test_copy_matches_version(self):
        self.assertEqual(changed_files(REPO), [])

    def test_edited_file_is_named(self):
        tmp = tempfile.mkdtemp()
        try:
            shutil.copytree(os.path.join(REPO, VENDOR), os.path.join(tmp, VENDOR))
            with open(os.path.join(tmp, VENDOR, "skills", "security-audit", "HUNTING.md"), "a") as f:
                f.write("\nlocal edit\n")
            self.assertEqual(changed_files(tmp), ["skills/security-audit/HUNTING.md: hash differs from VERSION"])
        finally:
            shutil.rmtree(tmp)

    def test_deployed_under_spec_audit_not_as_skill(self):
        with open(os.path.join(REPO, "targets.json")) as f:
            t = json.load(f)
        self.assertNotIn("security-audit", t["skills"])
        roots = [PROVIDERS[r]["skills"] for r in t["skills"]["spec-audit"] if PROVIDERS[r]["skills"]]  # unprobed: no root
        base = os.path.join(REPO, VENDOR)
        laid = places()
        for rel in copy_files(base) + ["integration"]:
            key = "%s/%s" % (VENDOR, rel)
            if os.path.basename(rel) in NOT_DEPLOYED:
                self.assertNotIn(key, t["files"])
                continue
            name = "METHOD.md" if rel.endswith("/SKILL.md") else os.path.basename(rel)
            self.assertEqual(sorted(laid[key]), sorted("%s/spec-audit/security/%s" % (r, name) for r in roots))
        for key in t["files"]:
            for place in laid.get(key, ()):
                self.assertFalse(re.search(r"/spec-audit/security/.*SKILL\.md$|/security-audit/", place), place)
            if key.startswith(VENDOR + "/"):
                self.assertTrue(os.path.isfile(os.path.join(REPO, key)), key)

    def test_pinned_security_references_integration_description(self):
        """Requirement: Pinned security references: the copy carries its integration description, whose material is
        the upstream method, and that file is not among the hashed upstream files."""
        base = os.path.join(REPO, VENDOR)
        fields = integrations.read_integration(base, "security-audit", os.path.join(VENDOR, "integration"))
        self.assertEqual((fields["points"], fields["tags"], fields["material"]),
                         (["audit"], ["security"], "skills/security-audit/SKILL.md"))
        self.assertNotIn("integration", copy_files(base))

    def test_spec_audit_names_existing_references(self):
        with open(os.path.join(REPO, "skills", "spec-audit", "SKILL.md")) as f:
            text = f.read()
        names = set(re.findall(r"security/([A-Za-z-]+\.md)", text))
        self.assertIn("METHOD.md", names)
        refs = {n for n in os.listdir(os.path.join(REPO, VENDOR, "skills", "security-audit"))} | {"METHOD.md"}
        self.assertEqual(names - refs, set())


if __name__ == "__main__":
    unittest.main()
