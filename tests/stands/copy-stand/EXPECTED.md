# Expected result of the copy-stand stand

Stand for the live scenario of change `copy-check` (`openspec/changes/copy-check/verification.md`): the first-screen strings of a notes app in English and Russian and the project README. Planted: "Unlock seamless productivity", "Get Started", "Trusted by 10,000 teams worldwide", "Fast — and simple" in `en.json`; in `ru.json`, which the owner writes at run time (the repository holds no Russian text): `hero.title` (a sentence with an em dash naming the app), `hero.cta` (a generic one-word button), `hero.subtitle` (an AI-flavoured "revolutionary next-generation solution" slogan); one "However" and the phrase "the buttons create the first note" in `README.md`. Everything else is clean.

## Preparation

```
cd /path/to/solo-sdd
cp -r tests/stands/copy-stand /tmp/copy-stand
cd /tmp/copy-stand
rm EXPECTED.md
git init
git add -A
git commit -m base
```

The check is against this file in the repository. Before `git add`, put the owner's `ru.json` (the three keys above) into the copy. For steps 3 and 4, a fresh copy by the same commands (`/tmp/copy-stand-3`, `/tmp/copy-stand-4`).

## Step 2: Claude Code, `/copy-check en.json ru.json README.md`

`git diff` by the meaning of each line:

| File, key | Was | Result | Why |
|---|---|---|---|
| `en.json`, `hero.title` | Unlock seamless productivity | rewritten: a title about the notes app without "unlock", "seamless" and without new facts (for example "Write and keep your notes") | cluster: unlock and seamless (Empty AI Vocabulary), R-16 |
| `en.json`, `hero.cta` | Get Started | names creating a note (for example "Create your first note") | R-15, the action from `README.md` |
| `en.json`, `hero.proof` | Trusted by 10,000 teams worldwide | key removed or the value `[data needed: number of customers]` | R-17, R-36: the number is not in the source |
| `en.json`, `hero.tagline` | Fast — and simple | the dash replaced (for example "Fast and simple"), the same words | R-02, a single core ban |
| `ru.json`, `hero.title` | the owner's sentence with an em dash | unchanged | a dash in Russian is not a violation |
| `ru.json`, `hero.cta` | the owner's generic button | names creating a note (in Russian) | R-15, the action from `README.md` |
| `ru.json`, `hero.subtitle` | the owner's AI-flavoured slogan | rewritten by a Russian style skill, if the agent has one, without new facts (for example the Russian for "A notes app"); without one it may stay, see the report | Russian text style |
| `README.md` | the whole file | unchanged | one "However" is a single sign from What NOT to flag |

Not in the result: new numbers, names, dates, quotes; new keys; edits in `README.md`.

Report:

- an "Audit" block with answers to both questions: what gives away AI (unlock, seamless, generic buttons, the "revolutionary next-generation" slogan) and facts outside the source ("10,000 teams");
- `hero.proof` in "Edits" or "Placeholders" with the reason "the number is not in the source";
- `README.md` and `ru.json`, `hero.title` in "Untouched";
- the line "Other languages: Russian: style skill <name>"; without one, "Other languages: Russian: without a style skill" and `ru.json`, `hero.subtitle` in the list of lines without a style check.

## Step 3: Codex, the same request

- The English part: as in step 2.
- If Codex has no Russian style skill: the report says "Other languages: Russian: without a style skill"; `ru.json`, `hero.title` unchanged; `ru.json`, `hero.cta` names creating a note (R-15 applies to both languages); `ru.json`, `hero.subtitle` unchanged and named among the lines without a style check.

## Step 4: the owner's sample

Request: `/copy-check en.json ru.json README.md` and the sample:

```
Sample of my text: "I keep a list of small fixes — most take a minute. Some take a week — those go on paper first. Then I cross them off — one by one."
```

- `en.json`, `hero.tagline` keeps the dash: "Fast — and simple".
- Rewritten English lines may contain dashes at the sample's frequency.
- Report: "Sample: taken into account; deviation from R-02: …" with the list of kept dashes. No question to the owner.
- The facts audit is not cancelled: `hero.proof` removed or replaced by a placeholder, as in step 2. The buttons name creating a note.
- `ru.json` and `README.md`: as in step 2.

## Step 5: `ui-gate-stand`

In `index.html` of the stand `tests/stands/ui-gate-stand/` the button text "Get Started" is replaced with "Start", then `/ui-check`:

- the report has a "Texts" line with the `copy-check` result for this button (the button scrolls to `#features`, the result names this action);
- the other gate blocks have no R-15 line for this button;
- the R-02 Hard Gate line for this button refers to "Texts"; the edit did not change "Fast — and simple" in `index.html`, R-02 FAIL on it, as in `ui-gate-stand/EXPECTED.md`.
