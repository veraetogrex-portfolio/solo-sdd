## Live Scenario

1. `echo "buy milk" > notes.txt`, `mkdir backups`, `chmod a-w backups`, then `python3 backup.py notes.txt` → stderr `gave up on notes.txt, tries: 3`, code 1.
2. `echo '{"process.retry-max": 2}' > backup.json`, then `python3 backup.py notes.txt` → stderr `gave up on notes.txt, tries: 2`, code 1.
3. `chmod u+w backups`, then `python3 backup.py notes.txt` → `copied notes.txt, tries: 1`, code 0, and `backups/notes.txt` holds `buy milk`.
4. `python3 -m unittest discover -s tests` → code 0.

## Needs

none

## Fallback

Not needed: the scenario needs nothing external.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
