"""Marks that put a test of solo-sdd's suite into the slow or the release tier.

`@marks.slow` and `@marks.release` go on a test method or a TestCase class. SOLO_SDD_TESTS=fast|slow|release runs
the marked tests of that tier and the tiers before it; with no variable every test runs. tests/run.py --tier sets it.
`examples(full)` is the example count of a property test that starts a process or creates a repository per example.
"""
import os
import unittest

TIERS = ("fast", "slow", "release")
TIER = os.environ.get("SOLO_SDD_TESTS")
if TIER is not None and TIER not in TIERS:
    raise SystemExit("SOLO_SDD_TESTS=%r is not a tier: %s" % (TIER, ", ".join(TIERS)))


def mark(name, tier):
    """A decorator that skips a test of tier `name` unless `tier` is unset or names it or a later tier."""
    runs = tier is None or TIERS.index(name) <= TIERS.index(tier)
    return unittest.skipUnless(runs, "%s test: SOLO_SDD_TESTS=%s runs it only from the %s tier" % (name, tier, name))


slow = mark("slow", TIER)
release = mark("release", TIER)


def examples(full, reduced=20, tier=TIER):
    """The full count in the release tier; elsewhere, an unset variable included, the reduced one, at least 20 and at
    most the full count."""
    return full if tier == "release" else min(full, max(reduced, 20))
