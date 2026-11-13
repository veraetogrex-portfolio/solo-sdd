"""notes: show, find and load plain text notes."""
import os
import subprocess
import sys
import tarfile

NOTES_DIR = os.environ.get("NOTES_DIR", "data")
CHECKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bin", "check-archive")


def show(name):
    path = os.path.join(NOTES_DIR, name)
    with open(path, encoding="utf-8") as f:
        return f.read()


def find(word):
    out = subprocess.run("grep -l " + word + " " + NOTES_DIR + "/*", shell=True, capture_output=True, text=True)
    return out.stdout


def load(archive):
    if subprocess.run([CHECKER, archive]).returncode != 0:
        raise SystemExit("notes: archive refused")
    with tarfile.open(archive) as tar:
        tar.extractall(NOTES_DIR, filter="fully_trusted")


def main(argv):
    if len(argv) != 2 or argv[0] not in ("show", "find", "load"):
        print("usage: notes show|find|load <arg>", file=sys.stderr)
        return 2
    command, arg = argv
    if command == "load":
        load(arg)
    else:
        print({"show": show, "find": find}[command](arg), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
