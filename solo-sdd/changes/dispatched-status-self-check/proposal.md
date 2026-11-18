# Proposal

## Why

In the settings-* run of 2026-11-17 (ten changes), `sdd-dispatch.py accept` refused three archived statuses (settings-delivery-items, settings-ci-wait, settings-local-merge). Each `LIVE` field carried a paraphrase or several output lines joined with " / " instead of a line the stand prints. Each refusal cost one `SendMessage` round trip to a finished orchestrator and one more acceptance. The orchestrator holds every input `accept` needs (`WORKTREE`, the `LIVE` and `VALIDATE` commands, `verification.md`), so it can run the same check before it hands back.

## What Changes

- In the "Under the dispatcher" mode of `spec-next`, before the last message the orchestrator writes its status block to a file outside `WORKTREE` and runs `python3 ~/.local/bin/sdd-dispatch.py accept <file>` on it.
- On mismatches (code 1 or 2) it corrects the stated field from the command's real output (the exit code, one printed line copied as is) or reworks the change, then repeats the check. It hands back `archived` only after `status matches`.
- The dispatcher's orchestrator prompt says the same in one line. The `LIVE` text after `->` is one line of the command's output, copied verbatim.
- The dispatcher still runs `accept` itself: the self-check saves a round trip, it does not replace the acceptance.

## Capabilities

### New Capabilities

### Modified Capabilities
- `spec-next-dispatched`: ADDED requirement Status self-check before handback.

## Impact

- `skills/spec-next/SKILL.md`
- `skills/spec-dispatch/orchestrator-prompt.md`
- `tests/stands/dispatched-status-self-check.py`

## Out of Scope

- A loose `LIVE` match in `sdd-dispatch.py accept`: whitespace-collapsed containment stays, and a paraphrase must still be refused.
- Running the `LIVE` command from the handback hook: a stand may take minutes, and hooks are fail-open.
- Neighbouring changes of this plan: `test-runner-deps-check`, `fix-settings-entry-scroll`, `fix-worktree-ignored-overwrite`, `fix-ci-wait-unread-checks`, `fix-stop-gate-worktree-config`, `fix-setup-links-exclude`.

## Depends On

none

## Source

"Да, заведи change" (the owner, 2026-11-18, on the follow-up list after the settings-* run, item: the orchestrator prompt should require the `LIVE` field to be one verbatim output line, since paraphrases happened three times)
