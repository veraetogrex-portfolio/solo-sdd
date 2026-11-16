5. **Creation.** For every unit: `solo-sdd new <name>`, then the artifacts in order, by the "Writing rules" section: proposal → specs → verification → tasks. `design.md` only when a decision cannot be recorded without it.
   - `Source` is the user's verbatim quote that gave rise to this change.
   - `Depends On` holds change names from step 3, or `none`.
   - `Out of Scope` includes the neighbouring units of the same plan.
   - `Impact`: in backquotes only paths of files and directories (from the project root) that the change creates, changes or deletes; function names, commands, words and languages without quotes. By the quoted paths the dispatcher decides which changes to run at the same time.
   - The requirement text (from `### Requirement:` to the first header, usually `#### Scenario:`) is at most 500 chars: `solo-sdd validate` fails above it. Examples and edge cases go into scenarios, several behaviours into separate requirements. A change that modifies a long requirement (`MODIFIED`) shortens it in the same delta: the behaviour does not change, the previous scenarios stay, what is moved out goes into scenarios or `ADDED`.
   - Every `#### Scenario:` has a WHEN (or GIVEN) step and a THEN step, written `- **WHEN** …`, `- **THEN** …`; a delta requirement stands only under `## ADDED`, `MODIFIED`, `REMOVED` or `RENAMED Requirements`; a requirement header has a space: `### Requirement: <name>`. `solo-sdd validate` fails on all three and on a requirement without a `#### Scenario:`.
   - A change being created modifies a requirement with the same name in the same capability as another change being created or already open (`solo-sdd/changes/*/specs/`, except `archive`): the later one gets the earlier one in `Depends On`.
   - A change changes the interface if the user sees its result on screen: a page, a panel, a widget, layout, styles. For such a change:
     - The first item of the What Changes list, right under the header, before all other items, is the line `Design Read: <screen> for <audience>, <style>, ENERGY n / RHYTHM n / MOTION n`. The audience comes from the "Audience" field of `DESIGN.md`, the style from the "Character" field; an empty field or no `DESIGN.md` gives "not specified".

       The direction is set only if `DESIGN.md` has the line `Dial: ENERGY n / RHYTHM n / MOTION n` with three numbers from 1 to 3; the template letters `n` mean not set. Do not derive dials from the user's words or the filled fields. Not set: ENERGY 1 / RHYTHM 1 / MOTION 1 and the mark "draft without direction" at the end of the line.
     - The Live Scenario is a list "element → action → expected result" for every control (button, link, form, menu) the change creates or changes, plus widths 1280 and 390 and every theme the interface supports. A form: "empty form → submit → a message about the unfilled field", "valid email → submit → a success message"; a mobile menu: "menu at 390 → open and close → opens and closes".
     - The user's business facts (their numbers, reviews, customer names, logos, photos of people): only those in `Source` or project files go into tasks and scenarios. The rest the task requires as an honest placeholder `[data needed: <what>]` and names it verbatim, separately for each kind of data (`[data needed: customer reviews]`, not `[data needed: …]`); `Needs` lists what is needed, `Fallback` says "the placeholder stays on screen".

       The change does not wait for this data and gets no `WAITING` file. The rule also applies in `demo` mode: there the product's working data is invented (a seed, an emulation), but not the user's business numbers, reviews and customers.
   - The change code reads foreign input: files, archives, documents or network data whose path or content arrive while the program runs (an argument, a request, the network, the user's choice), rather than lying in the project repository. Such a change gets one task of tests on hostile input in `tasks.md`. It belongs to the requirement that introduces reading this input and names only the items applicable to this input.

     If the change already has 10 tasks, the items are added to the existing test task. Applicability is decided by the input format, not by the intended parsing method: any archive has entry paths, even if it is not unpacked to disk. An inapplicable item is not written (an archive without XML gets no item about entities):
     - a limit on size and number of entries (ZIP bomb, compression ratio);
     - archive entry paths (`..`, absolute, links);
     - nesting depth;
     - XML entity expansion;
     - catastrophic regular expressions;
     - truncated and broken input;
     - escaping when inserting into code, HTML or a command.

     A change that reads only `AGENTS.md`, configs and the project's own files needs no such task.
