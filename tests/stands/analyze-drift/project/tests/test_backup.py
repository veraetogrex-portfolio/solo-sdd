import pathlib
import subprocess
import sys
import tempfile
import unittest

BACKUP = pathlib.Path(__file__).resolve().parents[1] / "backup.py"


class BackupTest(unittest.TestCase):
    def test_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            script, note = pathlib.Path(tmp, "backup.py"), pathlib.Path(tmp, "notes.txt")
            script.write_text(BACKUP.read_text())
            note.write_text("buy milk\n")
            run = subprocess.run([sys.executable, str(script), str(note)], capture_output=True, text=True)
            self.assertEqual(run.stdout, "copied %s\n" % note)
            self.assertEqual(pathlib.Path(tmp, "backups", "notes.txt").read_text(), "buy milk\n")


if __name__ == "__main__":
    unittest.main()
