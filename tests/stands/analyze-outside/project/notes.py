"""notes: add, list, edit and show the history of short text notes kept in notes.json."""
import datetime
import json
import pathlib
import sys

STORE = pathlib.Path(__file__).with_name("notes.json")


def load():
    return json.loads(STORE.read_text()) if STORE.exists() else []


def save(notes):
    STORE.write_text(json.dumps(notes, indent=1))


def main(argv):
    notes = load()
    today = datetime.date.today().isoformat()
    if argv[:1] == ["add"] and len(argv) == 2:
        notes.append({"id": len(notes) + 1, "versions": [{"text": argv[1], "date": today}]})
        save(notes)
        print("added %d" % len(notes))
    elif argv == ["list"]:
        for n in notes:
            print(n["id"], n["versions"][-1]["text"])
    elif argv[:1] == ["edit"] and len(argv) == 3:
        notes[int(argv[1]) - 1]["versions"].append({"text": argv[2], "date": today})
        save(notes)
    elif argv[:1] == ["history"] and len(argv) == 2:
        for v in notes[int(argv[1]) - 1]["versions"]:
            print(v["date"], v["text"])
    else:
        print("usage: notes.py add <text> | list | edit <id> <text> | history <id>", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
