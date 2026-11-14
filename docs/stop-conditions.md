# How solo-sdd stops

Two words place solo-sdd. The **harness** is what one agent run sees, may touch and how its result is checked: here it is the project's `AGENTS.md` and the global rules (`global/AGENTS.md`), the change artifacts (`proposal.md`, delta specs, `verification.md`, `tasks.md`), the `CLAIM` and `WAITING` markers, the worktree of a dispatched change, the hooks (`global/work_hooks.py`, `global/process-guard.py`) and the check commands from `AGENTS.md`.

The **loop** is what repeats runs until the goal is met: `spec-next` for one change (task, check, review round, live scenario, archive) and `spec-dispatch` for a wave of changes, one orchestrator per change.

The goal of the loop is not "tests green": a change is done when it is accepted by its spec, an agent that did not write it reviewed it, and its live scenario passed (`ALGORITHM.md`, Principles 4, 7 and 10). A run that does not reach the goal stops by rounds or by proof:

| Stop condition | What happens | Where it is enforced |
|---|---|---|
| One run, one change | The next change is not started | `skills/spec-next/SKILL.md`, step 11 |
| Review: at most three rounds | An open `Important` after the third: the findings and "reconsider the approach" go to `Not Verified`, no archive | `skills/spec-next/SKILL.md`, step 7a; `ALGORITHM.md`, step 5 |
| Reviewer failure | One rerun per round; a second failure in the round: the requirements without a verdict go to `Not Verified`, no archive | `skills/spec-next/SKILL.md`, step 7a; `ALGORITHM.md`, step 5 |
| The same edit did not help twice | Stop and find the cause; no third attempt the same way | `global/AGENTS.md`, section 3; `skills/relay/SKILL.md` |
| A running service: the second edit did not help | Stop and analyse; a third edit the same way is forbidden | `skills/debug-profile/SKILL.md`, "Two failures in a row"; `ALGORITHM.md`, step 6 |
| The live scenario failed, no allowed Fallback | No archive, the status is "not done" | `ALGORITHM.md`, step 7; `skills/spec-next/SKILL.md`, step 9 |
| Open CRITICAL or HIGH findings of `spec-analyze`, or a dependency from `Depends On` not archived | The change is not ready, `spec-next` takes another; under the dispatcher an unarchived dependency gives `not_ready` | `ALGORITHM.md`, gate G2; `skills/spec-analyze/SKILL.md`; `skills/spec-next/SKILL.md`, step 4a and "Under the dispatcher" |
| The change has another agent's `CLAIM` or a `WAITING` | The change is not taken; the hook refuses edits to it | `ALGORITHM.md`, step 5; `skills/spec-next/SKILL.md`, step 2; `global/AGENTS.md`, section 9; `global/work_hooks.py`, `guard` |
| The dispatcher's worktree misses something | `blocked` with what is missing | `skills/spec-next/SKILL.md`, "Under the dispatcher" |
| The session ends with work left | The `stop` hook returns the agent once while there are uncommitted edits, a ready change not archived, an open unmerged PR, an interface not checked in a browser or a reply in the wrong language; the `guard` hook refuses an `archived` status whose commit, archive or `CLAIM` do not match | `global/work_hooks.py`, `stop` and `guard` |
| Interface Hard Gate FAIL | One fix and one repeat of the check; a FAIL after it stays in the report, the interface is not ready | `skills/ui-check/SKILL.md`, step 8 and "Gate" |
| A codebase map file missing or empty | Its subagent runs once more; then the file is reported as not written | `skills/project-init/SKILL.md`, step 4a |
| A change grows past 10 tasks | It becomes several changes linked through `Depends On` | `ALGORITHM.md`, Principle 2 |
| Orchestrators at once | At most the "Orchestrators:" limit, 2 by default | `global/sdd_dispatch_plan.py` |
| Subagent depth below 2 | The dispatcher launches nobody | `skills/spec-dispatch/SKILL.md`, step 1 |
| An orchestrator status does not match the checks | One return to the orchestrator, a repeat means "not ready"; `not_ready` and `blocked` continue only by the owner's decision | `skills/spec-dispatch/SKILL.md`, step 6 |
| The dispatcher's returns | One return for a conflict (another for a conflict in other files), a red check, CodeQL alerts or a build failure after update, one CI rerun for `infra`, one repeat of `land`; a repeat ends as "not merged" with the reason | `skills/spec-dispatch/SKILL.md`, step 7 |
| Main is red after a merge, the main folder is not clean, or the branch touches an owner-only path | No new launches or merges and a question to the owner; "not merged"; the change waits for the owner | `skills/spec-dispatch/SKILL.md`, step 7 |
| The CI wait | A failed check that is not a test, no checks at all for 180 s, a required check that has not started for 300 s, or the whole wait over 1200 s gives `infra` | `global/sdd_pr.py` |
| A paid call, deleting or overwriting data, an action on prod | Stop and ask, naming what happens, how many calls and the amount | `ALGORITHM.md`, Principle 5; `global/AGENTS.md`, section 2; `skills/ship/SKILL.md`, step 2 |
| A secret in the diff | Stop and say so | `skills/ship/SKILL.md`, step 4 |
| A blocker without a workaround | What is unchecked goes to `verification.md` and `docs/waiting.md`, the rest gets closed | `ALGORITHM.md`, Principle 6; `global/AGENTS.md`, section 4 |
| `agent-quality` | Names the stop condition and the cost before a paid run | `skills/agent-quality/SKILL.md`, step 6 |

The other side of the same rules: the agent does not stop while there are unfinished items and no real blocker (`global/AGENTS.md`, section 2), and an orchestrator does not end its turn while its subagent or background command runs (`skills/spec-next/SKILL.md`, "Under the dispatcher").

There is no token budget, on purpose: the limits are counted in rounds and proofs, and the cost is held by the cheapest models in tests and by consent before every paid run (`ALGORITHM.md`, Principle 9).
