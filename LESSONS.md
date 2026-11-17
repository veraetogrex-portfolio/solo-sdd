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

## Lessons of this repository

*Source: the `## Lessons` section of `AGENTS.md`: each line there is the short rule, the full text is here under the same id; a refinement edits both.*

### stand-runs-what-it-tests

A stand runs what it means to test: a container stand gets the repository files and its downloads through stdin from the host (a container here has no network of its own and a bind mount sees only folders under the home folder), and a stand that runs a Python package with `-m` against a copy of the repository runs from outside the copy, since the working folder comes first on the import path; a stand that compares with the tree before its change pins that commit by hash, since the fork point from main and a lookup by the change's own commits move once the branch merges, and reads it through `git archive` or `git show` into a separate folder, never by a stash or a checkout of the working folder, which moves uncommitted work away under every process running on it; a stand reads a program's screen or stream once a condition on it holds, never after a quiet pause alone, and a property that compares two paths runs both whole on every example, the real command on its side, never only when the first one acted; a test that runs a copy of a project file copies every project module that file imports, so a new import does not break the copy.

### environment-facts

Detection of an installed agent or any other environment fact looks only inside the passed home and PATH, never at a machine-wide folder, and a test of such code pins what is detected, so it gives the same result on every machine; a setting proposed from detected facts requires every fact the command that uses it depends on, not only the one that makes it possible; a test fixture names every git default it relies on (the initial branch of each `init`, bare ones included), since the system git config differs between machines, and turns off git's detached auto maintenance in a repository it copies, which otherwise writes in it during the copy, also in an environment it rebuilds from a filtered copy; a test that expects a temporary home to stay unchanged runs its interpreters without bytecode caching, since macOS's own Python caches it under the home folder.

### probe-before-claim

A claim about how a tool behaves or what it outputs, taken from its changelog, its binary or another agent's report, is written into a skill, document, change or a command's own output only after running that tool here on a probe (with no run possible it is worded as expected and unconfirmed, never as a state), and a record of which files a change edited, or of which tests a source path affects, only after checking it against its source before the commit: the diff for the first, and for the second every way a test reaches the path (an import, a script another script starts, a copy it compares, a build run in the tree); text with escapes of non-ASCII characters is read back in the written file before the commit, since the writing tool may decode the escapes; a new test counts as checked only once the suite runner's own run of its file lists it (a test written after the file's `unittest.main()` guard passes when called by name and never runs under `tests/run.py`); a timing or cost measured on another machine or load is measured again here, base and branch under the same load, before a pass bar or a plan rests on it; a path given to a command that also takes a name or a shorthand in that place (`npm publish`, `npm install`) starts with `./`, and a publishing step runs once as the registry's dry run before the first tag.

### unnamed-product

An unnamed "our product" in a request means solo-sdd itself: the owner's other products are neither the subject of the work nor a source of its facts unless the owner names them.

### formats-read-like-their-program

Markup that hides text (HTML comments) is removed once, in the reader, after code blocks and code spans are recognised, and no later consumer applies it again; a command that reads a format another program reads (a document `validate` checks, a shell command line) reads it with that program's own rules or a copy of its reader, never a regex of allowed prefixes, and accepts exactly what it accepts or refuses it, and a command that copies a tree and then advises deleting the source refuses on any entry it cannot list, follow or decode, and a gate or report over a document counts every line outside the part it exempts and keeps the readable entries of a file it cannot fully parse: a line or entry skipped silently is lost; a command matches each argument exactly against its own options, answers `-h`/`--help` with its usage, and refuses any other argument before it reads its state or writes a file, never testing an option by membership and dropping the rest; a command that refuses a broken input checks it before its first side effect, also in the steps that run before its main one, and one that writes several files checks every target it can (readable, writable) before the first write, whichever order it writes in; in a fail-open handler an exception ends every later step, so a step that must always run comes before the steps that can raise, and each check loads a shared input (a policy file) through its own guarded read, so a broken input drops only the checks that need it; a reader of another program's log (a Claude Code transcript) takes a record from every form that program writes it in (a user entry, a queued attachment, an origin marker of the harness), read from its real output, and a sender it cannot place is not the person.

### probe-capabilities

A session capability the agents depend on (loopback sockets, network, subagent depth) is probed once before they are launched; its absence stops the launch with the fix named only when the project declares that it needs the capability, otherwise the launch goes on with the fix as a warning.

### output-checks-by-prefix

A check of a command's printed output finds a line by its prefix, not by its position, a check of a document reads a step or item whole up to the next one, not one physical line, and both collapse whitespace in both sides before comparing with a stated text: a new output line or a reflowed paragraph must not break old checks, and tools align output with runs of spaces.

### judgement-stands

A stand that grades a judgement call expects one answer only for an input where every correct reading gives it; otherwise it grades what all correct answers share.

### deployment-gates

A deployment gate is worded for the whole repository, not for one change: a push after any later merge deploys the whole tree, and a deployment the process starts for itself never takes a source that holds merged work not yet cleared for deployment; a publication step that hands a name others resolve to a new target (a repository renamed and its old name taken by a new one) first guards and repoints every clone that uses the name, and checks a push it forbids with a dry run, never with the push itself. A command that deploys or writes into the agents' folders is never run to learn its options (`sync.py push --help` ignored the flag and deployed): its usage is read from its source, and a probe of it runs in a temporary home.

### cleanup-scope

A cleanup of copies an earlier version or a gone source deployed skips every path the current deployment map still lays out, names its candidates instead of matching all unmapped state entries, and takes a source as gone only when it is missing, never when it cannot be read for lack of permission (a folder that can be listed but not entered included); a removal in a folder the owner also writes to deletes only the entries its own sources name (the map, the state, its caches), keeps and names every other entry, and silences only the one error it expects (a folder not empty).

### setting-sources

A value that falls back to a built-in default is reported with its source, so a reader can tell "nothing set" from a choice, and a reader that switches on a listing tells a refusal (a FAIL line, a non-zero exit) from an empty answer, so a broken input never reads as the thing being off; every reader of a setting, the command a person runs included, takes its chain of sources from one shared definition, never from a fallback only one reader knows; and a choice inferred from older records is stored explicitly once made, so records a later step keeps never infer it back; a rule that says which of several values (two command rows, two settings) its readers take is written at every reader that a change finds by searching for the value's name, not only where the values are defined; a gate that asks for a command's run selects what it asks about with that command's own selection (the same function, both sides normalized the same way), so every request it makes is one a run can clear.

### bulk-wording

A bulk wording replacement in instructions keeps quoted program output verbatim and is reread line by line for a shift of meaning.

### branch-scripts-from-commits

A script that moves or rewrites a branch decides from the commits themselves, never from a setting that other readers resolve from more sources than it does.

### input-edge-forms

An input check covers the edge forms of its input: a whole-number or name check accepts only ASCII digits and the whole string (`str.isdigit` passes digits that `int()` rejects, a regex `\d` with `$` passes other scripts' digits and a trailing newline), a check whether input comes from a terminal treats a closed stdin (no stream at all) as no terminal, and a comparison that decides whether to rewrite a stored value normalizes both sides the same way, line endings included; a write made atomic through a new file and a rename keeps every refusal of the write it replaces, checking the target's own write permission, since a rename needs only the folder's; text a reader takes from foreign input (a folder name, a line of a file) reaches its output only escaped, and a reader of a foreign tree refuses a link leading out of it before it prints anything read through the link; a stored result read back is checked against what the step that wrote it can produce, and printed exactly as stored, never cleaned a second way; a foreign command's process group is killed only while a process the caller has not yet reaped holds the group id; every reader of a file in a folder foreign input can reach opens it without blocking and parses only a regular file, and a result stored beside others in one record carries its own time, since the record's write dates every result it keeps; a check that tells a missing path from an unreadable one stats the path and catches only the not-found errors, never a library predicate (`Path.is_file`, `exists`) whose error handling changes between Python versions; an index into a list that a reread can shorten (a cursor, a selection) is brought into range at one point every reader passes, never after each reread, since a reread path that fails or returns early skips that fix. A screen bounds every line of variable length it draws (a folder path, a status, a message) to a set number of rows, so the selectable rows and the footer fit the smallest size whatever the input; wrapping such a line without a limit pushes them off the screen. A read moved out of a call site into a shared helper keeps every exception the old call site caught (a decode error is a `ValueError`, not an `OSError`), and a test of that broken input pins it. A limit on a call to a foreign service holds for the whole call at one point every caller passes: a time limit bounds the call with its name lookup, not each socket operation, and a once-a-day request is reached from every entry of a screen through that one gate, never by a second, blocking path beside it; a cut hint on a screen names only a key the selected row acts on.

### removed-requirement-tests

Before a stand or test of a removed requirement is deleted, every check it holds for a requirement that stays moves into a kept test.

### new-outcomes-where-read

A new outcome or exemption of a step is written where the rule it changes is read: before that step in the order, and as its exit in every state list the process keeps where that list's exit rule is written; otherwise the run takes the old path or waits for an event that never comes; a new ban is checked against every rule that requires what it bans, and names that rule's case as its exception.

### scenarios-only-new-code

A scenario of a change that adds a behaviour names what only the new code produces, and an example project's own checks are ones its shipped open change already meets: otherwise a test written first passes on the old code, or the agent rewrites the example before code; a plan for a feature a person uses covers its life around the request unasked (how it is found, kept current after an update, switched off, and what it shows when it fails or contradicts another source), not only the words of the request.

### gates-from-sources

A gate that a person's marks open counts the expected items from its own source and takes the person's confirmation from a record the agent's account cannot produce (a review the platform refuses the author), never from the marks alone or from parsing the agent's commands; evidence the agent writes itself (a LIVE command, a review field) is matched whole against a source written before the work, and the bypass flag of such a gate is the owner's alone.

### shell-guards

A guard that exempts part of a shell command (a message, a pattern, a path) reads it by the shell's grammar and each program's option grammar (clustered and abbreviated options, `$'…'`, a `#` comment, a `cd`, a wrapper that runs a word) and refuses every form it cannot read the same way: an exemption is kept as narrow as the forms it is proven on, and the fallback that drops it names the forms the reader can read (an allowlist), not every occurrence of a feared token; a check whether a pattern (a glob) reaches a protected name tests it against that name's own rule and the files that exist, never against a sample list of names; a reader of a nested part (a substitution, a `-c` string) takes it from the original text, never from a copy another reader rewrote (requoted, cut), and applies the same exemptions as at the top level; a guard that recognises a run behind wrappers and runners tries every later word instead of stopping at the first word it does not know, since that word may wrap the run: a false refusal is recorded as a known limit, a missed run is not; a form one rule learns to read stays unreadable for every other rule that refuses it for its own reason (a `${` computes a file name for the secret guard), so a scenario that expects a guard to pass is checked against every requirement of that guard on the same form; a fix that narrows or widens such a match is replayed against the forms the previous version decided, so no refused form starts passing and no command of another program starts being refused.

### ignored-paths

A path that becomes git-ignored is checked through every step that merges, resets, aborts or mirrors the tree for a deletion of its copy on disk: git treats an ignored file as expendable and overwrites or removes it, a transfer of ignored files carries their removal, and a gate that holds such a transfer for a person compares the copy with the snapshot the transfer merges from, never with the destination (an owner's edit there is no change of the branch), and counts a deleted copy as carried; an undo that runs after a reset deletes files git tracks again; a temporary copy of a git index keeps the index's own time, since git rereads only a file no older than the index it loads and a fresh copy hides an edit made in that second. A file a run creates in a working folder, such as a notes file, is made only where git ignores it or outside the work tree (the git common folder): an untracked copy stops a later merge of a branch that commits the same path.
