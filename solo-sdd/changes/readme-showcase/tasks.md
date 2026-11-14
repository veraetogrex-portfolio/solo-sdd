## 1. Reference into docs/

- [ ] 1.1 Move the reference sections of `README.md` verbatim into `docs/cli.md`, `docs/first-project.md`, `docs/settings.md`, `docs/integrations.md`, `docs/hooks.md`, `docs/stop-conditions.md`, `docs/agents.md`, `docs/migrate.md`, `docs/development.md`, rewriting only the in-page links; proof: Live Scenario step 2 prints `missing: 0`
- [ ] 1.2 Point the tests that read a moved section at its docs file (`tests/test_settings.py` Readme, `tests/test_providers.py` Readme, `tests/test_readme.py` StopConditions and test_links_resolve over every tracked `docs/*.md`, `tests/test_public_tree.py` test_only_installable_code over README and tracked `docs/*.md`), keeping every assertion; the known-bypass messages of `tests/test_work_hooks.py` and `tests/test_process_guard.py` and the comments of `solo_sdd/providers.py` and `global/work_hooks.py` name `docs/hooks.md` or `docs/agents.md`; `tests/affected.json` maps the new files; proof: `python3 tests/run.py --jobs 5 tests/test_settings.py tests/test_providers.py tests/test_public_tree.py tests/test_runner.py` green

## 2. The showcase README

- [ ] 2.1 Requirement Own features first: QUICK_MUST of `tests/test_readme.py` gets `solo-sdd install --hooks`, the OpenSpec check refuses the name on every README line (the scenario rows change with the MODIFIED requirement); proof: the test fails on the old README
- [ ] 2.2 Requirements Short README and Skills listed: two tests in `tests/test_readme.py` with rows for a grown README, an unlinked document, a new skill and a removed skill; proof: they fail on the old README
- [ ] 2.3 Write the new `README.md` (intro with badges, Quick start with `--hooks`, One change start to finish, Why, Skills, Requirements, Installation, Supported agents, How it stops, Update and uninstall, Docs, Contributing, License) and `CONTRIBUTING.md`; run `copy-check` on both; proof: `python3 tests/test_readme.py` and `python3 tests/test_demo.py` green

## 3. Checks

- [ ] 3.1 `python3 tests/run.py --jobs 5 --tier slow`, `python3 -m pyflakes solo_sdd global scripts sync.py` without output, `python3 -m solo_sdd validate --all`

## 4. Acceptance

- [ ] 4.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 4.2 Run `solo-sdd validate readme-showcase` and archive the change with `solo-sdd archive readme-showcase --yes`
