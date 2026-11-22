analyze add-retry: requirements 2, scenarios 3, tasks 5; covered 2/2
CRITICAL 1 · HIGH 6 · MEDIUM 2 · LOW 1, fixed 0

Retell:
- After a copy fails, `python3 backup.py <file>` tries it again in a loop until the retry limit.
- The limit comes from `backup.json`. The task names the key `process.retry-limit` and the delta names `process.retry-max`. The default is `5` in task 1.2 and `3` in the delta.
- On success the command prints `copied <file>, tries: <n>` and exits 0.
- When every try fails it prints `gave up on <file>, tries: <n>` to stderr and exits 1.
- New tests in `tests/test_retry.py` cover each scenario. They make the copy fail with a `backups/` folder that has no write permission.

| ID | Pass | Level | Where | Finding | What was done |
|---|---|---|---|---|---|
| A1 | 7, 7a | CRITICAL | `specs/retry/spec.md` "Retry a failed copy" vs main `solo-sdd/specs/backup/spec.md` "Copy a file"; proposal `Modified Capabilities` | The delta changes behaviour the main spec defines but has no MODIFIED requirement for `backup`, and `Modified Capabilities` is empty. For a successful copy the main spec prints `copied <file>` and the delta prints `copied <file>, tries: <n>`. For a failed copy the main spec prints `could not copy <file>: <reason>` and the delta prints `gave up on <file>, tries: <n>`, which drops the reason. These are two behaviours under one condition. | |
| A2 | 7 | HIGH | `tasks.md` 1.2 vs requirement "Default retry limit" | The default limit in task 1.2 is `5`, and the requirement and the "No settings file" scenario say `3`. | |
| A3 | 7 | HIGH | `tasks.md` 1.3 vs requirement "Retry a failed copy" | Task 1.3 reads the limit from `process.retry-limit`, and the delta, the scenario "A limit the person set" and the proposal name `process.retry-max` for the same setting. | |
| A4 | 1 | HIGH | proposal What Changes item 3; `Impact` `docs/retry.md` | No retell line, task or requirement covers `docs/retry.md`, which should explain the retry and its setting. | |
| A5 | 3, 7a | HIGH | `tasks.md` 1.2 check; `tests/test_backup.py` `test_copy` | The check of task 1.2 is "the old test included" passes. `test_copy` asserts stdout `copied <path>\n` exactly, and the new requirement prints `copied <file>, tries: <n>`. Both cannot hold, and no task updates `tests/test_backup.py`. | |
| A6 | 3 | HIGH | `tasks.md` 1.1; scenario "The second try works" | The method in task 1.1, a `backups/` folder without write permission, makes every try fail, so the test cannot produce "first try fails, second works". This scenario has no Live Scenario step either: step 3 checks `tries: 1`, so nothing checks it. Side issue: `chmod a-w` does not stop root, so whether the test fails on the current code depends on the environment. | |
| A7 | 5 | HIGH | `specs/retry/spec.md` both requirements | The spec does not say what happens when `backup.json` is unreadable or broken (invalid JSON), or when `process.retry-max` is not a positive integer (`0`, negative, a string). It also does not separate "no setting" (default 3) from "could not read the settings". The user sees the outcome either way. | |
| A8 | 5 | HIGH | requirement "Retry a failed copy" | The spec does not say which failures are retried. A missing source file would be tried 3 times and end in `gave up ... tries: 3`, which replaces today's `could not copy <file>: <reason>` and loses the reason the user needs. | |
| A9 | 5, 7a | MEDIUM | `specs/retry/spec.md`; `verification.md` step 2 | The spec does not say where `backup.json` lies. The project map in `AGENTS.md` says "next to" `backup.py`, and Live Scenario step 2 writes it into the current folder. Tests that run a copied script from a temp folder depend on which one the code reads. | |
| A10 | 3 | MEDIUM | `tasks.md` 1.2 check | The criterion "`python3 -m unittest discover -s tests` passes" is a "tests are green" proof. It does not name which tests from 1.1 this task makes pass. | |
| A11 | 6 | LOW | `tasks.md` 1.2 | "tries a failed copy again in a loop" names a method instead of a property, such as "at most the limit tries, stops at the first success". | |

Passes with no finding:
- Pass 2: the frame is complete. Out of Scope names `retry-pause`, Depends On is none, Source is a quote, there are 5 tasks with an Acceptance group of 2, Impact holds only paths, the requirements are 354 and 140 characters, and Needs has a Fallback.
- Pass 2, Hostile input: only the settings file `backup.json` is read.
- Pass 3a: no requirement is worded as "for any". Also, the project allows only the standard library.
- Pass 4: `process.retry-max` is read by `backup.py`, and the output and docs are read by the person.
- Pass 4a: the change adds no trust boundary.
- Pass 7b: there is no other open change.
- `solo-sdd/analyze.md` and `CLAUDE.md` are missing.

Ready for implementation: no. A1 (CRITICAL) has to be fixed before code: the delta contradicts the main `backup` spec and has no MODIFIED requirement. The task values in A2 and A3 have drifted from the requirements, and HIGH findings A4 to A8 are still open.
