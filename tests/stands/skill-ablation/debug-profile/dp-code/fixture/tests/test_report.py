import unittest

from app.report import summary


class Report(unittest.TestCase):
    def test_summary(self):
        self.assertEqual(summary("name,amount\na,1\nb,2\nc,3\n"), "total: 6")


if __name__ == "__main__":
    unittest.main()
