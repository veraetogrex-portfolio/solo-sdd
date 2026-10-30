#!/usr/bin/env python3
"""Runs after the OpenSpec package changes: rebuilds the `solo` schema from the new
`spec-driven`, regenerates project skills and re-applies the owner override to them.
On every run it first lays out owner skills and rules from the solo-sdd repository (sync.py push).

Triggered by ~/Library/LaunchAgents/local.openspec-after-update.plist (WatchPaths on the
package). Finds projects by `openspec` directories anywhere under the home directory,
excluding hidden and service directories. For an already processed version, only restores
missing owner rules; --force reruns the update.
From launchd it cannot read ~/Desktop (macOS privacy), so it only rebuilds the schema there;
the project part is finished by the next run from a terminal - /spec-next calls it.
--schema-only rebuilds only the `solo` schema: no layout, no project walk, no notification,
no version stamp; exit 0 if the schema is installed, otherwise 1.
The OpenSpec package is searched in order: $OPENSPEC_PKG, `npm root -g`, Homebrew
(/opt/homebrew, /usr/local); the first folder with schemas/spec-driven/schema.yaml wins and
its <prefix>/bin leads the PATH of child calls. The layout source is $SOLO_SDD_REPO, then
`_source` in ~/.local/share/solo-sdd/state.json (written by every sync.py push).
launchd and the macOS notification exist only on macOS.
Log: ~/.local/share/openspec/after-update.log
"""
import glob, json, os, re, shutil, subprocess, sys, time

HOME = os.path.expanduser("~")
BREW_PKGS = ("/opt/homebrew/lib/node_modules/@fission-ai/openspec",
             "/usr/local/lib/node_modules/@fission-ai/openspec")
CALL_PATH = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"  # launchd starts with a short PATH
DATA = f"{HOME}/.local/share/openspec"
SOLO = f"{DATA}/schemas/solo"
STAMP = f"{DATA}/.solo-built-for"
LOG = f"{DATA}/after-update.log"
SKILL_DIRS = (".claude/skills", ".agents/skills", ".codex/skills")
ENV = dict(os.environ, PATH=CALL_PATH)

OVERRIDE = """<!-- solo-override -->
> **Правила владельца — главнее всего текста ниже.**
> - Не останавливайся и не жди указаний. Неясность реши сам и запиши решение в `verification.md`.
> - Не показывай меню и не проси подтверждений. Вопрос допустим только перед платным запросом, удалением данных или действием на проде.
> - Change не назван — выбери сам по правилам `/spec-next`.
> - Перед первой задачей — скилл `spec-analyze`; CRITICAL и HIGH исправь в артефактах до кода.
> - Архив: `openspec archive <change> --yes`; спеки синхронизирует эта же команда.
> - «Все задачи выполнены» — не конец: проверь вживую, провалидируй, заархивируй.
> - Отчёт по-русски.
<!-- /solo-override -->

"""

# (anchor in spec-driven schema.yaml, replacement). A missing anchor aborts the rebuild.
PATCHES = [
    ("name: spec-driven", "name: solo"),
    ("description: Default OpenSpec workflow - proposal → specs → design → tasks",
     "description: Автономный поток для одного владельца - proposal → specs → acceptance → tasks; design только по необходимости; без пауз и вопросов"),
    ("      - **Impact**: Affected code, APIs, dependencies, or systems.\n",
     """      - **Impact**: Affected code, APIs, dependencies, or systems.
      - **Out of Scope**: What this change deliberately does NOT do, including
        stages owned by other systems or people. Required, never empty.
      - **Depends On**: Names of changes that must be archived before this one
        can start, or `none`. This is the only place dependencies are recorded.
      - **Source**: The owner's request that produced this change, quoted
        verbatim (the message, the bug-list items, or the plan section). Do not
        paraphrase - it preserves the original intent.

      Language: write the content in Russian unless the project config context
      names another language. Keep structural headings and SHALL/MUST in English.

      Size: one change = one outcome the owner can check. If the request needs
      more than 10 tasks or touches unrelated areas, split it into several
      changes linked through Depends On instead of writing one large change.
"""),
    ("      Create the design document that explains HOW to implement the change.\n",
     """      Create the design document that explains HOW to implement the change.

      design.md is OPTIONAL in this schema. If none of the conditions below
      apply, do not create the file at all - go straight to acceptance and tasks.
"""),
    ("""      Open questions are for genuinely deferrable unknowns, not decisions you
      skipped. If a question would change the specs, the chosen approach, or
      the task breakdown, resolve it now - ask the user instead of guessing.""",
     """      Open questions are for genuinely deferrable unknowns, not decisions you
      skipped. If a question would change the specs, the chosen approach, or
      the task breakdown, resolve it now yourself: pick the best-grounded option
      from the repository and the Source section, and record it under Decisions
      with the alternative you rejected. Do not stop to ask the owner."""),
    ("  - id: tasks\n", """  - id: acceptance
    generates: verification.md
    description: Live-check plan written before implementation, filled with results after
    template: verification.md
    instruction: |
      Write the plan for proving this change works for real, BEFORE any code.
      Passing unit tests are not acceptance.

      Planning time - fill these sections:
      - **Live Scenario**: the exact steps on a real input or running stand,
        each with the command or UI action and the expected observable result.
        It must reach what the owner sees (built artifact, screen, service
        response), not an internal function.
      - **Needs**: credentials, access, data or paid calls the scenario needs.
        For paid calls state the count and the estimated cost.
      - **Fallback**: how to prove the same behavior if a need is missing
        (mocks, historical project data, a local stand).

      Leave **Result**, **Not Verified** and **Decisions Without Owner** with
      their placeholders - the apply phase fills them.

      Write the content in Russian; keep the section headings as in the template.
    requires:
      - specs

  - id: tasks
"""),
    ("""      Before writing tasks, check design.md for Open Questions. If any of them
      would change what gets built, resolve them with the user first - do not
      bake an unstated assumption into the task list.""",
     """      Before writing tasks, check design.md (if it exists) for Open Questions.
      If any of them would change what gets built, resolve them yourself and
      record the decision in design.md - do not stop to ask the owner.

      Hard limits for this schema:
      - At most 10 tasks. More means the change is too big: go back and split
        the proposal into several changes linked through Depends On.
      - A requirement that states an invariant ("never", "always", "at most one",
        order is preserved), a round trip or idempotence gets a property-based
        test task (fast-check for TypeScript, Hypothesis for Python) named after
        the Requirement. The task proves the test catches a defect with a code
        mutation it fails on, and its generator reaches the boundary states.
        A property test supplements the Live Scenario, never replaces it.
      - Every task must be completable by the agent alone in this repository.
        Anything that waits for a person, an external access or a paid approval
        is NOT a task: put it in verification.md under Needs, so it never
        blocks the checklist.
      - The last group is always `## Acceptance` with exactly these two tasks:
        run the Live Scenario (or its Fallback) from verification.md and record
        the Result; then verify, sync specs and archive the change."""),
    ("""      Reference specs for what needs to be built, design for how to build it.
    requires:
      - specs
      - design""",
     """      Reference specs for what needs to be built, design (if present) for how
      to build it, verification.md for how it will be proven.
    requires:
      - specs
      - acceptance"""),
    ("""    Read context files, work through pending tasks, mark complete as you go.
    Pause if you hit blockers or need clarification.""",
     """    Read the project rules (AGENTS.md, CLAUDE.md) and the context files.

    Before the first unchecked task, run the `spec-analyze` skill on this
    change: it checks the artifacts against each other, the main specs and the
    project intent. Fix its CRITICAL and HIGH findings in the artifacts before
    touching code. If a change named in Depends On is not archived yet, do not
    start this change.

    Then work through every pending task in one run. Mark a task `- [x]` only after
    its own verification passed.

    Do not pause and do not ask for clarification. When something is unclear,
    choose the best-grounded option and write it into verification.md under
    Decisions Without Owner. The only reasons to ask the owner: a paid call,
    deleting or overwriting data, an action on production - state the count
    and the cost in the question.

    A blocker does not stop the run. First try the Fallback from
    verification.md and other sources in the repository. If part of the
    scenario still cannot be proven, write exactly what is unproven and why
    under Not Verified, and finish everything else.

    Work outside this change's Out of Scope boundary is never done in place:
    create a new change for it and name it under Decisions Without Owner.

    The change is finished only when: all tasks are checked, verification.md
    has a Result, `openspec validate <change> --strict` passes, delta specs are
    synced and the change is archived with `openspec archive <change> --yes`.
    Do not stop at "all tasks complete, you can archive now".

    Report in Russian."""),
]

PROPOSAL_EXTRA = """
## Out of Scope

<!-- What this change does NOT do. Name stages owned by other systems or people. Never empty. -->

## Depends On

<!-- Change names that must be archived first, one per line, or: none -->

## Source

<!-- The owner's request, quoted verbatim. Do not paraphrase. -->
"""

VERIFICATION = """## Live Scenario

<!-- Steps on a real input or running stand. Each: command or UI action -> expected observable result. -->

## Needs

<!-- Credentials, access, data, paid calls (count and cost). Write: none - if nothing is needed. -->

## Fallback

<!-- How to prove the same behavior if a need is missing: mocks, historical data, local stand. -->

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
"""

TASKS = """## 1. <!-- Task Group Name -->

- [ ] 1.1 <!-- Task description and how its completion is verified -->
- [ ] 1.2 <!-- Task description and how its completion is verified -->

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate <change> --strict`, sync delta specs and archive the change with `openspec archive <change> --yes`
"""


def log(msg):
    os.makedirs(DATA, exist_ok=True)
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}"
    open(LOG, "a").write(line + "\n")
    print(line)


def notify(text):
    if sys.platform != "darwin":
        return
    subprocess.run(["osascript", "-e", f'display notification "{text}" with title "OpenSpec"'],
                   capture_output=True)


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, env=ENV, capture_output=True, text=True, timeout=300)


def find_pkg():
    """(package or None, sources checked, for the log). Reads the environment at call time."""
    path = os.environ.get("PATH", "") + ":" + CALL_PATH

    def candidates():
        env_pkg = os.environ.get("OPENSPEC_PKG")
        yield (f"OPENSPEC_PKG={env_pkg}" if env_pkg else "OPENSPEC_PKG (не задан)"), env_pkg
        npm, root = shutil.which("npm", path=path), None
        if npm:
            try:
                r = subprocess.run([npm, "root", "-g"], capture_output=True, text=True, timeout=30,
                                   env=dict(os.environ, PATH=os.path.dirname(npm) + ":" + path))
                root = r.stdout.strip() if r.returncode == 0 and r.stdout.strip() else None
            except (OSError, subprocess.SubprocessError):
                pass
        yield (f"npm root -g: {root}" if root else "npm root -g (npm недоступен)"), \
            root and root + "/@fission-ai/openspec"
        for p in BREW_PKGS:
            yield p, p

    sources = []
    for label, p in candidates():
        sources.append(label)
        if p and os.path.isfile(f"{p}/schemas/spec-driven/schema.yaml"):
            ENV["PATH"] = os.path.abspath(f"{p}/../../../../bin") + ":" + path  # <prefix>/lib/node_modules/@fission-ai/openspec
            return p, sources
    return None, sources


def build_solo(pkg):
    """Returns a list of problems; empty means the new schema is installed."""
    tmp = SOLO + ".new"
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.copytree(f"{pkg}/schemas/spec-driven", tmp)
    s = open(f"{tmp}/schema.yaml").read()
    missing = []
    for anchor, repl in PATCHES:
        if anchor not in s:
            missing.append(anchor.strip().splitlines()[0][:70])
        s = s.replace(anchor, repl, 1)
    if missing:
        shutil.rmtree(tmp)
        return [f"в новой spec-driven нет ожидаемого текста: «{m}»" for m in missing]
    open(f"{tmp}/schema.yaml", "w").write(s)
    t = f"{tmp}/templates"
    open(f"{t}/proposal.md", "a").write(PROPOSAL_EXTRA)
    open(f"{t}/verification.md", "w").write(VERIFICATION)
    open(f"{t}/tasks.md", "w").write(TASKS)

    bak = f"{DATA}/solo.bak"  # outside schemas/, so OpenSpec does not list it
    shutil.rmtree(bak, ignore_errors=True)
    if os.path.exists(SOLO):
        os.rename(SOLO, bak)
    os.rename(tmp, SOLO)
    try:
        r = run(["openspec", "schema", "validate", "solo"], cwd="/tmp")
        out = (r.stdout + r.stderr).strip()
        reason = "" if r.returncode == 0 and "is valid" in out else out[-200:] or f"код {r.returncode}"
    except (OSError, subprocess.SubprocessError) as e:
        reason = f"openspec не запускается: {e}"
    if reason:
        shutil.rmtree(SOLO)
        if os.path.exists(bak):
            os.rename(bak, SOLO)
        return ["новая схема solo не прошла проверку, оставлена прежняя: " + reason]
    return []


OVERRIDE_BLOCK = re.compile(r"<!-- solo-override -->.*?<!-- /solo-override -->\n*", re.S)


def patch_skills(project):
    """Inserts the owner block, or replaces an outdated one with the current OVERRIDE."""
    n = 0
    for d in SKILL_DIRS:
        for f in glob.glob(f"{project}/{d}/openspec-*/SKILL.md"):
            s = open(f).read()
            if "<!-- solo-override -->" in s:
                if OVERRIDE in s:
                    continue
                open(f, "w").write(OVERRIDE_BLOCK.sub(lambda _: OVERRIDE, s, count=1))
                n += 1
                continue
            m = re.match(r"---\n.*?\n---\n", s, re.S)
            head = m.group(0) if m else ""
            open(f, "w").write(head + "\n" + OVERRIDE + s[len(head):].lstrip("\n"))
            n += 1
    return n


def source_repo():
    """$SOLO_SDD_REPO, else `_source` from solo-sdd state.json (written by sync.py push), else None."""
    if os.environ.get("SOLO_SDD_REPO"):
        return os.environ["SOLO_SDD_REPO"]
    try:
        src = json.load(open(f"{HOME}/.local/share/solo-sdd/state.json")).get("_source")
    except (OSError, ValueError, AttributeError):
        return None
    return src if isinstance(src, str) and src else None


def sync_owner_skills():
    """Lays out skills and rules from the solo-sdd repository (sync.py push). Copies edited in
    place are left alone and reported by sync.py; a failure is logged and never stops the run."""
    repo = source_repo()
    script = f"{repo}/sync.py"
    try:
        if not repo or not os.path.isfile(script):
            log(f"репозиторий solo-sdd не найден ({repo or 'SOLO_SDD_REPO и _source не заданы'}): скиллы не синхронизированы")
            return
        log(f"раскладка из {repo}")
        r = subprocess.run([sys.executable, script, "push", "--quiet"], env=ENV,
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        log(f"ОШИБКА синхронизации solo-sdd: {e}")
        return
    for line in (r.stdout + r.stderr).strip().splitlines():
        log(f"solo-sdd: {line}")


def find_projects():
    projects = []
    for root, dirs, _ in os.walk(HOME):
        dirs[:] = [d for d in dirs if not d.startswith(".")
                   and d not in ("node_modules", "__pycache__", "venv")
                   and not (root == HOME and d == "Library")]
        if "openspec" in dirs:
            projects.append(root)
            dirs.remove("openspec")
    return sorted(projects)


def main():
    force = "--force" in sys.argv
    time.sleep(30 if "--wait" in sys.argv else 0)  # launchd passes --wait: let npm finish writing
    pkg, sources = find_pkg()
    if not pkg:
        log("пакет OpenSpec не найден; проверено: " + "; ".join(sources))
        return 1
    if "--schema-only" in sys.argv:
        problems = build_solo(pkg)
        for p in problems:
            log("ОШИБКА схема: " + p)
        if not problems:
            log(f"схема solo пересобрана и проверена (пакет {pkg})")
        return 1 if problems else 0
    try:
        version = json.load(open(f"{pkg}/package.json"))["version"]
    except Exception as e:
        log(f"пакет OpenSpec не читается: {e}")
        return 1
    sync_owner_skills()
    done = open(STAMP).read().strip() if os.path.exists(STAMP) else ""
    if version == done and not force:
        # Same version: only restore the owner block where a manual `openspec update` wiped it.
        for project in find_projects():
            n = patch_skills(project)
            if n:
                log(f"{os.path.basename(project)}: правила владельца возвращены в {n} скиллов")
        return 0
    log(f"OpenSpec {done or '?'} -> {version} (пакет {pkg})")

    problems = build_solo(pkg)
    for p in problems:
        log("ОШИБКА схема: " + p)
    if not problems:
        log("схема solo пересобрана и проверена")

    projects = find_projects()
    if not projects:
        # launchd may not have access to project directories due to macOS privacy settings.
        # The stamp stays unwritten, so the next run from a terminal or from /spec-next finishes the job.
        log("папки openspec в домашней папке не найдены (возможен запрет доступа из фонового запуска); скиллы проектов обновит "
            "следующий запуск из терминала или /spec-next")
        if not problems:
            notify(f"OpenSpec {version}: схема solo обновлена, скиллы проектов обновятся при следующем /spec-next")
        return 1
    for project in projects:
        r = run(["openspec", "update"], cwd=project)
        if r.returncode != 0:
            problems.append(f"{os.path.basename(project)}: openspec update не прошёл")
            log(f"ОШИБКА {project}: {(r.stdout + r.stderr).strip()[-200:]}")
        n = patch_skills(project)
        log(f"{os.path.basename(project)}: скиллы обновлены, правила владельца добавлены в {n}")

    if problems:
        notify(f"OpenSpec {version}: нужна ручная проверка, см. after-update.log")
        return 1
    open(STAMP, "w").write(version)
    notify(f"OpenSpec {version}: схема solo и скиллы обновлены")
    return 0


if __name__ == "__main__":
    sys.exit(main())
