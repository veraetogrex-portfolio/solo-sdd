import pathlib
import subprocess
import sys
import tempfile
import unittest

NOTES = pathlib.Path(__file__).resolve().parents[1] / "notes.py"


class NotesTest(unittest.TestCase):
    def test_add_list_edit_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = pathlib.Path(tmp, "notes.py")
            script.write_text(NOTES.read_text())
            run = lambda *a: subprocess.run([sys.executable, str(script), *a], capture_output=True, text=True).stdout
            run("add", "buy milk")
            run("edit", "1", "buy oat milk")
            self.assertEqual(run("list"), "1 buy oat milk\n")
            self.assertEqual([l.split(" ", 1)[1] for l in run("history", "1").splitlines()], ["buy milk", "buy oat milk"])


if __name__ == "__main__":
    unittest.main()
