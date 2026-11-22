"""backup: copy a file into the backups/ folder next to this script."""
import pathlib
import shutil
import sys

BACKUPS = pathlib.Path(__file__).with_name("backups")


def main(argv):
    if len(argv) != 1:
        print("usage: backup.py <file>", file=sys.stderr)
        return 2
    BACKUPS.mkdir(exist_ok=True)
    try:
        shutil.copy2(argv[0], BACKUPS / pathlib.Path(argv[0]).name)
    except OSError as e:
        print("could not copy %s: %s" % (argv[0], e), file=sys.stderr)
        return 1
    print("copied %s" % argv[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
