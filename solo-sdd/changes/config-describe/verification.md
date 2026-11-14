## Live Scenario

1. In a temporary git repository, `solo-sdd init --yes < /dev/null`, then `solo-sdd config describe delivery.mode` → lines naming `delivery`, a description sentence, `local, pr`, default `local`, team default `pr`, the value in effect and its source.
2. `solo-sdd config set mode team`, then `solo-sdd config describe delivery.merge-by` → value `human`, source `mode`.
3. `solo-sdd config describe` → one block per registered key and per pattern key, in registry order.
4. `solo-sdd config list --json | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d), all(r['about'] for r in d))"` → the number of registered keys and `True`.
5. `solo-sdd config list` → the same lines as before the change (compare with the output of the commit before it).
6. `solo-sdd config describe delivery.color; echo $?` → the known keys listed, `1`.

## Needs

none

## Fallback

Not needed: every step runs locally.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: the docs table check was planned as new → dropped from the requirement — the existing `Readme` test of `tests/test_settings.py` already keeps `docs/settings.md` on the registry keys, so a new test would not fail first
- analyze: describe of pattern keys and of a broken file was open → patterns after the registered keys, then the pattern keys set in the file; a broken file refused as `config list` refuses it — one reader of the file, one refusal
