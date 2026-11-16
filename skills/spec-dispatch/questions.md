9. **Questions to the user.** A decision needed from the user goes at once into an `AskUserQuestion` window (deferred: load it through `ToolSearch`) with options, the recommended one first. The orchestrators work in the background; their statuses, merges and launches come after the answer. No window (a `claude -p` session): the question goes as the first line of the message marked "Needs from you", the other changes continue without waiting.

   Every answer that changes the plan of the run (a shared path, an ignored dependency, a kept or removed marker, a kept dependency, the orchestrator limit, the order, taking or dropping changes, a delivery mode step 0 could not record) is written at once, before the next recalculation, as one line appended to `<decisions file>` (step 0), under the run's heading: `- <time> <change or path>: <decision> — <the key it gives the planner>`, `no key` when the planner takes none.

   For example `- 14:05 package-lock.json: shared — --shared package-lock.json`, `- 14:07 fix-pin: marker kept — no key`, `- 14:07 fix-pin: ignore cli-participants — --ignore-dep fix-pin:cli-participants`.

   Abandoned markers: the options `Remove and launch` (recommended) and `Keep`, the question text holds the ids and reasons from `waiting:`.
   - "Remove and launch": recalculate by step 2, `rm <MAIN>/solo-sdd/changes/<id>/CLAIM` only for those named in the question whose reason is still `CLAIM abandoned` (do not touch live markers), recalculate again.
   - "Keep": the markers stay, the change stays in `waiting:` until the end of the run and in the report with the reason, the question is not repeated.
   - No window: the question as a "Needs from you" line, the markers are not removed: that is "Keep".

   Unknown dependencies (`unknown dependency` in `waiting:`): names marked "a spec, not a change" get one question, options `Ignore` (recommended) and `Keep`; other names get one question, `Keep` (recommended) and `Ignore`: it could be a typo in a real dependency. One kind of names, one question; both kinds, two questions in one window. The question text holds the ids and names from `waiting:`.
   - "Ignore": `--ignore-dep <id>:<name>` until the end of the run, recalculate, the line "Remove from Depends On: <names>" in this change's orchestrator prompt; `MAIN` files are not edited.
   - "Keep": the change stays in `waiting:` until the end of the run and in the report, the question is not repeated.
   - No window: a "Needs from you" line, that is "Keep".

   A proposal to change the course of the run that you cannot accept yourself (running in parallel changes the plan holds because of a shared file, taking new changes into the run, stopping the run) goes into a window at the moment you formulated it, not as a line in a status message. For a shared file the options are `Treat <path> as shared until the end of the run` (`--shared <path>`, recalculate) and `One at a time`. Nothing is launched against the script's plan.

   You do not need to edit `proposal.md` or `AGENTS.md`: the user writes the file into "Shared:", suggest it in "Needs from you" of the report.
