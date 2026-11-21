## Live Scenario

1. `python3 notes.py add "buy milk"`, `python3 notes.py add "call Ann"`, `python3 notes.py edit 1 "buy oat milk"`, then `python3 notes.py export out.zip` → `exported 2 notes to out.zip`, code 0.
2. `python3 -m zipfile -l out.zip` → one entry `notes.json`; its note 1 has the versions `buy milk` and `buy oat milk`.
3. `python3 notes.py export out.zip` again → code 2, stderr names `out.zip`, the file is unchanged.
4. `python3 notes.py export new.zip --merge out.zip` → `exported 4 notes to new.zip`, code 0; the notes from `out.zip` have ids 3 and 4.
5. `python3 -m unittest discover -s tests` → code 0.

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
