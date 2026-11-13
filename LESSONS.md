# Lessons

Every rule of the algorithm appeared after a specific defect. Collected here, in general form, are the ones that cost the most. Each section names its source. Project details stay in the project's own skills.

## A spec for an executor

*Source: a consumer project, defect analysis.*

- **A property, not a method.** The spec "look for the substrings commit and push" missed `git merge`. Later the same check fired on the word "merge" in `merge-conflict` and on the phrase that forbade commits.
- **A test must fail on the current code.** A check field was made mandatory and filled in all tests, but never executed. The executor broke exactly the declared test, and the unit counted as a success.
- **Structure, not line numbers.** An executor fixes exactly the listed places. Describing the structure ("every place where an escape of the outer language stands inside a template string") found six places instead of the two named.
- **Mandatory, not optional.** An optional port method with no implementation hid from the compiler that a whole interface was missing: the button rendered and did nothing. The method was made mandatory, and the compiler showed the debt at once.
- **Whatever the source knows is asked from the source.** A model list "hard-coded as a fallback" is an invented value.
- **Branching on an agent's name is a future edit in the same place.** Ask for a CLI property, not its name. A consumer project collected twenty-two such places.
- **The "do it yourself" header is mandatory.** Without it the executor returns a plan and waits for an answer nobody will give, and the wave is wasted. It happened on the very first unit.
- **Every new value has a named consumer.** "Computed and read by nobody" is the most persistent defect class: eight cases, and tests caught none.
- **A paired check.** A point fix of one of two similar places almost always leaves the second copy.

## What counts as proof

*Source: a consumer project, defect analysis.*

- **Green checks ≠ it works.** Four times all checks passed while the product did not work.
- **An executor's report is not proof.** Seven tasks were marked closed while the code was missing. A rule against this was written in advance and did not fire, because the orchestrator set the mark from the report.
- **Checking against the spec is routine in every wave.** One run gave 87 findings on 71 requirements, three of them critical. Because of them the orchestration results could not be trusted either way.
- **Check what a person gets.** The built artifact, not the source. A unit test does not prove the result reached the interface.

## Orchestration

*Source: a consumer project, analysis of orchestration runs.*

- **Split by file ownership, not by topic.** Two units on one file conflict, however different their tasks are.
- **The composition root is a bottleneck.** The file that assembles the whole application is needed by almost every wiring task. Debts on it pile up and are paid by a separate unit at the end of the wave.
- **Unit size is counted in proofs, not files.** The unit "three ban checks" actually needed six probes and took twice as long as its neighbours.
- **A report does not say where the executor worked.** The edits went into an old copy of the repository in a temporary folder: an hour of work and 124 thousand tokens. Check `git status` of your own tree and full paths.
- **An executor that broke off has already written files.** A restart gets the note "work started and broke off, continue".
- **Quota and overload are different refusals.** Eight parallel executors use up the daily quota in about an hour.
- **Do not measure the tree while a wave is writing.** Otherwise you get failures that an isolated run does not have.
- **Writing the spec and launching the executor are separate calls.** Glued into one command, three times in a row they launched the executor from a foreign directory, without write access to the repository.
- **The orchestrator does not write code.** When the quota ran out, the orchestrator started editing itself: it inserted a handler into the middle of someone else's expression and broke the build. (A lesson of the `codex-orchestration` executor mode; since 08.11.2026 the rule is replaced by principle 7 of `ALGORITHM.md`: the lead agent writes the code itself from the start.)

## Property-based tests

*Source: a consumer project, follow-up queue test, 09.10.2026.*

- **A green property test on working code proves nothing.** Of five planted mutations, the first version of the test caught three.
- **The generator must reach boundary states.** By default `fast-check` builds short sequences, and the reply never reached the retry limit: the limit check stayed silent. What helped: length up to 80 steps with a uniform distribution and operations aimed at a reply in flight.
- **A property written out from the spec catches what examples do not.** Confirming delivery of the wrong reply was caught by none of 19 example tests. The property test catches it in every run.

## Tools and process

*Source: process setup, 09.10.2026.*

- **One copy per rule.** Skills had two or three copies each in agent folders. A mechanical replacement of "Claude" with "Codex" spoiled two of them (`.Codex/settings.local.json`, "Codex tokens bill separately from Codex quota"). Now the source of truth is this repository, and `sync.py` shows an edit in place instead of overwriting it.
- **An insertion that skips what is already inserted never updates.** The owner's rules block in OpenSpec skills did not update after a text edit: the script saw the marker and moved on, so the new rules never reached projects. Now it compares the content.
- **A package manager rewrites what is not its own.** `npm install` of one package removed the `libc` fields from dozens of other lockfile entries and reformatted `package.json`. A dependency is added by a point insertion, and the diff is checked.
- **A hook and a skill describe the same file differently.** `spec-next` said to write `CLAIM` as `<agent> <date>`, while the write hook recognised as its own only a `CLAIM` with a session id, so the agent ran into its own marker (17.10.2026). The hook tests were green because they wrote `CLAIM` in the hook's format themselves. The format of a file read by both the agent and the hook is set in one place, and the hook test takes it from the agent's instruction.
- **A hook learns about the previous call late.** The Claude Code transcript is appended with a delay, and PostToolUse finishes after the next call has started. An edit hook that checks the transcript or the PostToolUse result does not see a `CLAIM` created by the command right before it. Besides, after a failed command with `cd` the session folder does not change. The decision is made by a synchronous PreToolUse by the time of its own commands: "CLAIM changed while a command of this session that names CLAIM and the change was running". The state for this goes into a separate append-only file: the async hook rewrites the shared json and would lose the entry. All three failures were found only by a live check; the tests were green.
