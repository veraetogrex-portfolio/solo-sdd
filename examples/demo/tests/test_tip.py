"""Tests of tip.py by the requirements of solo-sdd/specs/tip/spec.md."""
import os
import subprocess
import sys
import unittest

TIP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tip.py")


def run(*args):
    return subprocess.run([sys.executable, TIP, *args], capture_output=True, text=True, stdin=subprocess.DEVNULL)


class TipAndTotal(unittest.TestCase):
    def test_usual_bill(self):
        r = run("40", "15")
        self.assertEqual((r.returncode, r.stdout), (0, "tip 6.00, total 46.00\n"))

    def test_rounding_half_up(self):
        self.assertEqual(run("10.10", "15").stdout, "tip 1.52, total 11.62\n")


class WrongInput(unittest.TestCase):
    def test_negative_bill(self):
        r = run("-5", "15")
        self.assertEqual((r.returncode, r.stdout), (2, ""))
        self.assertIn("bill", r.stderr)

    def test_not_a_number(self):
        for args in (("abc", "15"), ("40", "nan"), ("40", "-1")):
            r = run(*args)
            self.assertEqual((r.returncode, r.stdout), (2, ""), args)


if __name__ == "__main__":
    unittest.main()
