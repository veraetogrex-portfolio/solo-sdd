---
name: codex-orchestration
description: Orchestrate the Codex CLI as a fleet of single-purpose executors instead of editing the repo directly. Decompose the request into independent units, give each unit its own codex process with its own spec, then review each diff from a clean context. Use this whenever a repository task involves heavy exploration (reading many files, grepping registries, following existing patterns), spans more than one area of the codebase, or is large enough that doing it inline would bloat the context. Also use it when the user says "use codex", "delegate this", "split this up", "run it through codex", "review the diff independently", or complains about context burn and compaction. Default to this flow for implementation work in a repo, not to direct editing.
---

# Codex orchestration

Act as the orchestrator. Codex processes do the reading and the typing; the orchestrator decides what the units of work are, writes their specs, verifies the results, and owns every judgement call.

The rule that shapes everything below: **one task, one agent.** Never hand a single Codex process a list of things to do.

## Why this shape

**Reconnaissance costs more than the edit.** Reading twenty files, grepping a registry, comparing five similar entries runs to tens of thousands of tokens. Pushed into a Codex process, only a diff and a short report come back.

**Compaction is the real multiplier.** Once the orchestrator's context overflows, the whole history gets re-summarized and every later turn carries that summary. One or two compaction cycles cost more than the entire conversation preceding them. Keeping heavy reads outside means those cycles never start.

**A spec is smaller than the work it describes.** "Add an entry to file X modeled on Y, with values A/B/C" is one or two thousand tokens instead of thirty thousand of independent wandering.

**Clean context catches more.** A reviewer that never saw the reasoning does not inherit its mistakes. Fewer rework rounds is the largest indirect saving.

**One task per agent keeps all of the above true.** An agent given three tasks reads for all three at once, so its context carries task A's noise into task C's edit — the exact contamination this flow exists to prevent. It also produces one tangled diff instead of three reviewable ones, and one failure kills all three. Separate processes stay small, stay independent, can run in parallel, and fail one at a time.

## Prerequisites

The `codex` CLI must be installed and permitted to run without an interactive prompt. In Claude Code that means an allow list in `.claude/settings.local.json`:

```json
{ "permissions": { "allow": [
  "Bash(codex:*)",
  "Bash(git worktree:*)",
  "Bash(<the project's package manager>:*)",
  "Bash(<the project's runtime>:*)"
] } }
```

Fill the last two from the project actually in front of you — `pnpm`/`npm`/`node`, `uv`/`python`, `cargo`, `go`, `make`. If the file is git-excluded (commonly via `.git/info/exclude`), never commit it. When a `codex` call stalls, the allow list is the first thing to check.

## Invocation

Pipe the spec through stdin from a file. Passing it as an argument lets PowerShell or bash mangle quotes and newlines.

```bash
# executor
codex exec --color never --sandbox workspace-write -C <repo> - < specfile

# reviewer
codex exec --color never --sandbox read-only -C <repo> - < specfile
```

`--color never` keeps ANSI escapes out of the returned text. `read-only` for review is not cosmetic: it guarantees the reviewer cannot quietly fix what it flags, so the report stays a report.

## Step 0 — Decompose

Before writing any spec, split the request into units. This is the step that decides whether everything downstream works.

A unit is well sized when it satisfies all four:

- **One outcome.** Describable in a sentence with no "and then".
- **Bounded surface.** A named, short set of files. If the file list is "wherever it turns out to be needed", the unit is not yet understood — do the reconnaissance first, then split.
- **Independently verifiable.** There is a command or an inspection that tells you this unit alone succeeded.
- **Self-contained spec.** Everything the executor needs fits in a spec you can write without further research.

Signals a unit is too big: the spec needs numbered phases; it touches unrelated areas of the tree; verifying it requires several different commands; you cannot predict which files it lands in.

Signals a unit is too small: the spec is longer than the resulting edit; it cannot be verified on its own; splitting only creates coordination overhead. Mechanical one-liners are cheaper done inline than delegated.

Then map the dependencies between units and sort them into waves:

- **Independent units** (disjoint file sets, no shared new symbols) run in the same wave, in parallel.
- **Dependent units** run in a later wave. If B needs a type, export, or migration that A creates, B waits for A to land and verify.
- **Units that would touch the same file** never run in the same wave. Two processes writing one file in one tree corrupt each other's work. Either serialize them, or give each its own `git worktree` and merge afterwards.

Present the decomposition to the user before launching anything: the unit list, what depends on what, and which will run in parallel. This is the cheapest possible moment to catch a misunderstanding — after launch, a wrong split costs a whole wave. Exception: under `spec-next` the plan is already agreed in the change's `tasks.md` and the run is autonomous — write the units, dependencies and waves into the report and launch without waiting.

## The loop, per unit

| # | Who | What |
|---|-----|------|
| 1 | you | Gather facts for this unit and write a precise spec |
| 2 | codex `workspace-write` | Makes the edits — this unit only |
| 3 | you | Run the project's verification, filtered to this unit's files |
| 4 | codex `read-only` | Independent review of this unit's diff |
| 5 | you | Verify each finding against authoritative sources, then fix |

Do not collapse steps. Skipping step 1 turns the executor into a wanderer and destroys the savings; skipping step 4 gives up the cheapest bug-catch available.

After a parallel wave, run one extra review over the **combined** diff. Per-unit reviews each saw a slice; nobody has seen how the slices fit together. Duplicated helpers, clashing names, and half-wired registrations live exactly in that gap.

## Writing the spec

The spec is the product of step 1 and it is where the orchestrator's value sits. It should leave no research for the executor — every fact it would otherwise hunt for goes in the file.

- **Do-it-yourself header, before everything.** "Make the edits now. Do not ask for confirmation, do not describe a plan and wait — nobody will answer. Done means files changed on disk and checks run." Without it an executor returns a plan and waits, and the wave is wasted.
- **Scope fence, first line.** What this unit is, and that nothing else is to be touched. The executor will see interesting adjacent problems; tell it to report them, not fix them.
- **Exact file paths**, plus an explicit boundary (`edit only under <dir>/`) when parts of the tree are stale, generated, or unused.
- **A pattern to copy.** Name an existing element that is structurally identical: "follow the shape of X". This is worth more than any amount of prose description.
- **Every literal value.** Identifiers, slugs, prices, limits, flags, defaults, fallbacks. The values you had to look up are precisely the ones an executor guesses wrong.
- **The contract**, when a later unit depends on this one — the exact signature, export name, or schema, so the two halves meet.
- **What not to touch.** No reformatting, no drive-by refactors, no dependency changes, no unrelated fixes.
- **No commits, no pushes.** State it in every spec.
- **What to report**: files changed, plus anything the spec left ambiguous.

Example shape:

```
Task: add the <item-id> entry to <path/to/registry>. This unit only.

Copy the structure of the existing <sibling-id> entry in the same file.

Values:
  id: <...>            slug: <...>
  <field>: <...>       <field>: <...>
  fallback: <...>

Do not modify anything outside <dir>/. Do not reformat neighbouring entries.
Do not commit or push; leave changes in the working tree.
Report the files you touched and anything this spec did not cover.
```

If a fact is genuinely unknown, say so and instruct the executor to flag it rather than invent it. An invented value looks exactly like a real one in a diff.

## Running a wave in parallel

Launch the wave's processes together, each with its own spec file, and collect the results as they land. When two units in a wave cannot avoid the same file, isolate them in a worktree under the temp folder — never next to the project, and never with `codex --worktree` (it puts the copy in `~/.codex/worktrees`); the work hook blocks both:

```bash
git worktree add "${TMPDIR:-/tmp}/wt-<unit>" <branch>
codex exec --color never --sandbox workspace-write -C "${TMPDIR:-/tmp}/wt-<unit>" - < spec-<unit>
# verify inside the worktree, then merge back, then: git worktree remove "${TMPDIR:-/tmp}/wt-<unit>"
```

Keep waves small enough that you can actually read every diff that comes back. Parallelism that outruns review is just faster bug production.

## Verification

Find the project's own checks rather than assuming a stack: look at `package.json` scripts, `Makefile`, `pyproject.toml`, `Cargo.toml`, CI config. Typical shapes are a typecheck, a lint, a build, and a test command; run from the directory that owns them, which in a monorepo is the package root, not the repo root.

Many branches carry pre-existing failures unrelated to the current work. Establish that baseline **before** the first executor runs — otherwise there is no way to tell inherited noise from damage just caused. Then filter each run's output to the unit's files and judge only its own impact. Reporting the whole error wall as a failure wastes a round trip.

## The review pass

Give the reviewer the same scope fence and a read-only sandbox:

```
Review the uncommitted changes in <paths for this unit> (git diff).
Check: consistency with sibling elements, correctness of literal values,
missing registration or export, anything this change breaks.
Report findings as a list. Do not edit any files.
```

Findings are hypotheses, not verdicts. Check each against an authoritative source — upstream docs, the actual registry, the real type definition — before changing anything. A confidently wrong review finding is the main way this flow injects bugs.

## Hard rules

- One task, one agent. A spec that describes two outcomes is two specs.
- Never commit or push unless explicitly told. Work stays in the working tree on the current branch.
- Never commit local permission or settings files that are git-excluded.
- Accept by the tree, not by the report: after each unit run `git status` in your own repository and check full paths. An executor can report a flawless success from a stale copy of the repo elsewhere.
- The orchestrator does not re-read what an executor already read. If you find yourself opening the same twenty files, the spec was too thin — fix the spec, not the context.
- Codex tokens bill separately from Claude quota. That is an accounting fact, not a licence to run sloppy loops.
