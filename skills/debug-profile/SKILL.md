---
name: debug-profile
description: Use when a running service or deployed project misbehaves and the cause is not obvious - "it does not work", "I do not see the data", "I do not see the tables", "we pushed to prod and nothing is there", "the project does not start", "we keep fixing in circles with zero result", "why do you fix the same thing 10 times", a production error log, or local and server results differ - and for a bug in code without a service: a failing test, a wrong function result. A project profile plus a stage-by-stage diagnosis, or a code bug path without the profile.
---

# debug-profile: debugging with a project map

The skill gives debugging facts about the project (what runs where, where the config comes from, where it is safe to look) and its own diagnosis steps below. Without the facts debugging guesses. A bug in code with no running service (a failing test, a wrong function result) skips the profile and takes section 3.

## 1. Project profile

Open `docs/debug-profile.md`. No file: create it by the template, filling it from the repository, `.env` (key names only), docker/compose, CI and deploy instructions.

```
# Debug profile
Mode: demo | prod
What triggers the deploy: <merge into main / tag push / a manual script>
Where it runs: <server, containers, URL, workflow>
How to learn the deployed version: <command>
Config and secrets: <files, variables; where they are set on the server>
Logs: <command or path for every stage>
Data: <databases, tables, what must not be touched>
Paid calls: <which models and APIs; a cheap model for checks>
Safe read-only access: <commands>
Stop before: <actions that need consent>
```

## 2. Diagnosis

1. **Reproduction.** The same scenario in which the problem is visible. Record what was expected and what was got.
2. **Version and environment.** Does the deployed commit match the expected one, did the service pick up the new variables (`.env` updated: was the container restarted?).
3. **Input data.** Is it there at the stage's input, in the right format and period.
4. **Localisation.** Walk the chain by logs stage by stage and find the first one where the result diverges from the expectation. No logs at a stage: add them first.
5. **Hypothesis.** One, checkable. Before the edit, choose the observation that will confirm or refute it.
6. **Fix** within the allowed boundaries, then the same scenario from step 1.
   In a project with `solo-sdd/` the fix is made as a bug fix change (`spec-plan`, the "Bug fix" section): the reproduction and the cause from steps 1 and 4 go into its proposal.

Read logs, statuses and configs yourself, without questions. A restart on prod, changing data and a paid run only after consent: name the action, the effect on data and the amount.

## 3. A bug in code

No service runs, the bug is in code: the profile is not needed, start here.

1. **Reproduction.** Make it a failing test: the smallest input that gives the wrong result, the expected value in the assertion. No failing test: no fix yet.
2. **Trace back.** From the wrong value walk back along the call chain, caller by caller, to the first place where the value is already wrong. The cause is there, not where the error shows.
3. **Comparison.** Find a working example: a similar call that gives the right result, in this code or in its history (`git log -p`, `git bisect`). List every difference between the two.
4. **One hypothesis.** Name one cause and the observation that confirms or refutes it, check it, then the next. Do not change two things at once.
5. **Fix.** In a project with `solo-sdd/` the fix goes through the "Bug fix" section of `spec-plan`: the failing test of step 1 and the place `file:line` of step 2 go into its proposal. Then the failing test passes and the other tests stay green.

## 4. Two failures in a row

The second edit did not help: stop. Record which hypothesis is refuted and by what. Check what is usually skipped: the deployed version, environment variables, access rights, the data schema, the cache, the time zone. A third edit the same way is forbidden.

## Report

```
Symptom: <what the user sees>
Cause: <stage and why> | not found — <what is ruled out>
Proof: <log, request, command output>
Fix: <what was changed> | consent needed for <action>
Check: <the same scenario, where it ran, the result>
Profile updated: yes | no
```

## Mistakes

| Thought | What to do |
|---|---|
| "I will fix it once more, it should work" | First an observation that tells the hypotheses apart |
| "It works locally, so it works on prod too" | Check the version and the variables on the server |
| "The user did not add the key" | Look at `.env` and the server: maybe they already did |
| "There are no logs, I will guess" | Add logs to the stage |
| "I will restart the container, it is quick" | On prod only with consent |
