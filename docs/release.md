# Releases

A release publishes the same three files to PyPI and npm: the sdist `solo_sdd-<v>.tar.gz` (the tracked tree without the `solo-sdd/` development log), the wheel `solo_sdd-<v>-py3-none-any.whl` built from that sdist and the npm tarball `solo-sdd-<v>.tgz`. They are built and published only by `.github/workflows/release.yml` from a pushed tag `v<v>`, never from a working folder: a build in a working copy that holds files git does not track (a personal skill, `global/claude-*`) can pack them, and `scripts/release_check.py` refuses such files.

## One-time setup

0. The repository is public: npm provenance is refused for a private source repository, and the README links on the PyPI and npm pages lead to it. The `release` workflow fails on a private repository before it builds. Do not make the private repository public: its history holds `solo-sdd/changes/archive/`, whose `verification.md` files hold local paths (`/Users/<name>/...`) and agent session ids. The archive is no longer tracked (`.gitignore`), but the history keeps it. Rename it to `solo-sdd-private` and publish a new repository under its name `veraetogrex-portfolio/solo-sdd`, which `pyproject.toml`, `package.json`, the README and the trusted publishers below name, by [Publication without the private history](#publication-without-the-private-history). The release files do not carry `solo-sdd/` either way.
1. GitHub, repository Settings → Environments: create `pypi` and `npm`. For each, a deployment tag rule `v*`; a required reviewer (the owner) makes every publish wait for one click.
2. PyPI, with two-factor authentication on: Account → Publishing → add a pending publisher. PyPI project name `solo-sdd`, owner `veraetogrex-portfolio`, repository `solo-sdd`, workflow `release.yml`, environment `pypi`. Add it before the first tag: without it the PyPI job of `release` fails with `invalid-publisher` (no publisher matches). The first release creates the project; no token is stored.
3. npm, with two-factor authentication on. npm accepts a trusted publisher only for a package that already exists, and refuses a token that bypasses two-factor authentication for a direct publish, so the first version is published once by hand from the owner's terminal: after the `release` run has built the files (download its `dist` artifact into `dist/`, or run `python3 scripts/release_check.py v<v>` in a clean clone), `npm login`, then `npm publish ./dist/solo-sdd-<v>.tgz --registry https://registry.npmjs.org`. Leave the secret `NPM_TOKEN` of the environment `npm` unset.
4. After the first version is on npm: npmjs.com → `solo-sdd` → Settings → trusted publisher → GitHub Actions: organization `veraetogrex-portfolio`, repository `solo-sdd`, workflow `release.yml`, environment `npm`. Then in Settings → Publishing access choose "Require two-factor authentication and disallow tokens". Later versions publish through the trusted publisher with provenance.

## Publication without the private history

The owner's step, a prod action: an agent never runs it, nor the rename, the repository creation or the push. It gives the public repository one root commit of the tracked tree; the change archive and the other ignored files stay out of it, and later work and release tags go to the public repository. The guard and the new remote address come first: once the public repository takes the old name, a clone whose remote still names that address pushes there.

1. Before anything changes on GitHub, with no agent running, in the working folder of the private repository on an up-to-date `main` whose `git status --porcelain` is empty, run:

```sh
cp scripts/pre-push-guard.sh "$(git rev-parse --git-path hooks)/pre-push"
chmod +x "$(git rev-parse --git-path hooks)/pre-push"
git remote rename origin private
git remote set-url private https://github.com/veraetogrex-portfolio/solo-sdd-private.git
```

Every worktree of the folder shares its hook and remotes. Every other clone of the private repository (another machine, a CI checkout) is deleted before step 2 and cloned again from the public repository after step 4: the guard arms only where `history-private` exists. Until step 2 a push to `private` fails: the new address does not exist yet.

2. GitHub: rename the private repository, Settings → General → Repository name `solo-sdd-private` (or `gh repo rename solo-sdd-private --repo veraetogrex-portfolio/solo-sdd`). GitHub lets a new repository take the old name; the redirect from the old name then ends.
3. Create an empty public repository `veraetogrex-portfolio/solo-sdd`: no README, license or `.gitignore` (`gh repo create veraetogrex-portfolio/solo-sdd --public`). `<public URL>` below is its address, `https://github.com/veraetogrex-portfolio/solo-sdd.git`.
4. In the same folder, run:

```sh
git checkout --orphan public-main
git commit -q -m "solo-sdd: first public commit"
git branch -m main history-private
git branch -m public-main main
git remote add origin <public URL>
git push -u origin main
```

The old `main` stays as the local branch `history-private`, tracking `private/main`. The `pre-push` hook `scripts/pre-push-guard.sh` replaces any earlier one, also the one `scripts/publish-first.sh` installed: it refuses a push of a commit that shares history with `history-local` or `history-private`, under any name and to any remote, `private` included, and of a ref that is not a commit (a tag on a file), and passes deletions and branches cut from the new `main`. So no old change branch or tag is pushed from this folder after step 4.

Then check: `git ls-remote origin` names only `refs/heads/main`, a clone of it has one commit and no `solo-sdd/changes/archive/` path, and `git push --dry-run origin history-private` ends with `pre-push: refused` (a dry run runs the hook and sends nothing). The private history is never pushed to the public repository. Changes now start from the new `main`; an open change branch of the old history is redone from it, since the guard refuses its push.

## A release

1. A change sets the new version in `package.json` and `solo_sdd/__init__.py` (`pyproject.toml` reads the second), adds the section `## <v>` to `CHANGELOG.md` listing as `- <change>` the changes archived since the previous version, and is merged into `main` by its PR. The section is the text of the GitHub release.
2. Optional, on any machine with Node 20+: `python3 -m pip install build` and `python3 scripts/release_check.py v<v>` from a clean clone. It prints the three files with their sizes, `wheel --version: <v>`, `npm --version: <v>` and `ok release v<v>`; any `fail` line is the reason it stops.
3. `git checkout main && git pull && git tag v<v> && git push origin v<v>`.
4. `gh run watch` on the `release` run; with a required reviewer, approve the `pypi` and `npm` deployments.
5. Check from a clean environment: `pipx run --spec solo-sdd==<v> solo-sdd --version` and `npx -y solo-sdd@<v> --version` print `<v>`.

## CI and delivery

`.github/workflows/test.yml` runs the `slow` tier of `tests/run.py` on Ubuntu for every push and PR, the `release` tier on macOS only for a `v*` tag (macOS minutes cost more; `release.yml` runs the Ubuntu tests of a tag) and both on a manual run (Actions → test → Run workflow). A newer run of the same ref cancels the older one, a run on `main` included.

An agent merges a PR only when `sdd-pr.py wait <url>` gives `CI: green`, through `sdd-pr.py merge`, which refuses a PR whose checks are not green. On `CI: red`, `CI: infra` or `CI: codeql` the agent fixes, reruns and waits again as `/ship` (under the dispatcher, `spec-dispatch`) says; a PR that is still not green waits for the owner: an agent never merges around a red or missing check.

## When a run fails

- `fail version` or `fail tag`: the tag and the version fields differ. Delete the tag (`git push origin :refs/tags/v<v>`, `git tag -d v<v>`), fix the version by a change, tag again.
- `fail tag ... is not on main`: tag a commit of `main`.
- `fail changelog`: `CHANGELOG.md` has no section for the version, or the section lists nothing. Delete the tag as above, add the section by a change, tag again.
- `fail repository ... is private`: make the repository public (step 0), then Re-run all jobs.
- A failure after one registry got the version: run the workflow again (Re-run failed jobs). Each publishing job skips a version its registry already has, and the GitHub release step uploads the files again.
- PyPI never takes the same version twice, even after a delete: a broken published version is fixed by the next patch version.
