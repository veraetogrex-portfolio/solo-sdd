"""notes: show, find and load plain text notes."""
import os
import sys
import tarfile

NOTES_DIR = os.environ.get("NOTES_DIR", "data")


def show(name):
    root = os.path.realpath(NOTES_DIR)
    path = os.path.realpath(os.path.join(root, name))
    if os.path.commonpath([root, path]) != root:
        raise SystemExit("notes: %s is outside the notes folder" % name)
    with open(path, encoding="utf-8") as f:
        return f.read()


def find(word):
    names = []
    for entry in sorted(os.listdir(NOTES_DIR)):
        path = os.path.join(NOTES_DIR, entry)
        if os.path.isfile(path):
            with open(path, encoding="utf-8", errors="replace") as f:
                if word in f.read():
                    names.append(entry)
    return "".join(n + "\n" for n in names)


def load(archive):
    with tarfile.open(archive) as tar:
        tar.extractall(NOTES_DIR, filter="data")


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
