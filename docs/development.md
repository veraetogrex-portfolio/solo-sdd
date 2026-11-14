# Developing solo-sdd

## Updating the deployment

A skill or rules edit goes into the repository, then the deployment:

```bash
cd solo-sdd
python3 sync.py status
python3 sync.py push
```

`push` does not overwrite a copy edited in place after the last deployment (for example, Codex added to a skill right in `~/.codex/skills`). Such a copy is marked `drift` and skipped. To pull the edit into the repository:

```bash
cd solo-sdd
python3 sync.py pull spec-next
git diff
python3 sync.py push
```

If copies in different folders were edited differently, `pull` asks for the source: `--from ~/.codex/skills`. `push --force` overwrites edits in place too. Before any overwrite the previous text is saved to `~/.local/share/solo-sdd/backup/`.

A whole file at a target path that solo-sdd did not lay out (`status` shows `first`, for example another tool's `~/.claude/skills/ship/SKILL.md`) is kept: `install`, `update` and `push` print `foreign <path>: kept (install --replace-foreign replaces it)`, lay out the rest and exit with code 1; `--replace-foreign` on any of the three saves it to a backup and replaces it, the other files of its folder stay. A file equal to its source is adopted as `ok`.

A rules file (`~/AGENTS.md`, `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md`) keeps its text and gets the block. A run that writes a backup keeps the 20 newest run folders of `backup/` (by the time in the folder name, then by modification time; a folder named by the time alone is one an earlier version wrote), deletes the older ones and prints `pruned backups: <n>`; an entry with another name stays.

`state.json` is written through a new file and an atomic replace; a `state.json` that cannot be read, does not parse or is not a JSON object stops `status`, `install`, `update`, `uninstall`, `sync pull`, `doctor` and `sync.py` with exit code 1 and `fail state: <path>: <reason>`, before any file changes; a missing one is a fresh deployment.

## Releases

A release is a tag `v<version>` on a `main` commit whose `package.json` and `solo_sdd/__init__.py` hold that version. `.github/workflows/release.yml` runs the tests and `python3 scripts/release_check.py <tag>` (the versions, the sdist, the wheel built from it and the npm tarball, each file tracked by git, a `--version` run of each), then publishes the same files to PyPI and npm through trusted publishing and creates a GitHub release with them.

`CHANGELOG.md` names the changes each version archived; the release check refuses a version without its `## <version>` section, and that section is the text of the GitHub release. The one-time registry setup and the release steps: [docs/release.md](https://github.com/veraetogrex-portfolio/solo-sdd/blob/main/docs/release.md).

## Checks

```bash
cd solo-sdd
python3 -m pip install --user hypothesis
python3 tests/run.py --tier slow < /dev/null
python3 -m solo_sdd validate --all
```

A round of checks while coding runs `python3 tests/run.py --tier fast`, then `python3 tests/run.py --affected <path>...`; the run before a release tag is `python3 tests/run.py --tier release`. The marks are in `tests/marks.py`; a direct `python3 tests/<file>.py` runs every test of the file.

The scripts in `global/` are deployed one file each, so some code blocks live in several `.py` files between the lines `# <name>:begin` and `# <name>:end`. A shared block is edited only in its source file (the `SOURCES` table of `scripts/sync_blocks.py`), then `python3 scripts/sync_blocks.py` copies it into every other file with those markers and names each rewritten copy; `--check` writes nothing and names each stale copy, and the copy tests run it.

A begin without its end, an end without its begin, a block twice in a file, a name without a source, a scanned folder it cannot list, a link to a folder or a `.py` file, a file with a lone CR line break or a copy it cannot write stops the script with code 1 before any write.

## What is not here

- Skills of a specific project live in that project.
- Skills unrelated to development stay in the agent folders, `sync.py` does not touch them.
