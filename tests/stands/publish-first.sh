#!/usr/bin/env bash
# Live Scenario stand of change github-publish: the first publication of solo-sdd on a clone of the current commit.
# Real git and pre-push hook, a bare repository instead of GitHub, a fake gh in PATH.
# The stand does not touch the real GitHub or the real HOME: the README "Installation" section runs under a temporary HOME.
# Run from the repository root: bash tests/stands/publish-first.sh (python3 with Hypothesis in PATH).
# HEAD is cloned, so the stand sees only what is committed.
set -euo pipefail

SRC=$PWD
[ -f "$SRC/scripts/publish-first.sh" ] || { echo "Run from the root of the solo-sdd repository." >&2; exit 1; }
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT

ok() { echo "ok: $*"; }
die() { echo "FAILED: $*" >&2; exit 1; }

# --- a. clone with history
git clone -q "$SRC" "$T/repo"
cd "$T/repo"
git checkout -q -B main
git remote remove origin
git branch change/old
deny=$(git -C "$SRC" rev-parse --path-format=absolute --git-common-dir)/info/public-denylist.txt
if [ -f "$deny" ]; then
  mkdir -p .git/info
  cp "$deny" .git/info/public-denylist.txt
fi
ok "clone with history: main, change/old"

# --- b. fake gh and c. identity
mkdir "$T/bin"
cat > "$T/bin/gh" <<GH
#!/usr/bin/env bash
case "\$1 \$2" in
  "api user") echo veraetogrex-portfolio ;;
  "repo view") echo "GraphQL: Could not resolve to a Repository with the name 'x'. (repository)" >&2; exit 1 ;;
  "repo create") git init --bare -q "$T/remote.git" && git remote add origin "$T/remote.git" ;;
  "repo edit") exit 0 ;;
  *) echo "gh: unexpected call: \$*" >&2; exit 2 ;;
esac
GH
chmod +x "$T/bin/gh"
export PATH="$T/bin:$PATH"
export GIT_AUTHOR_NAME=stand GIT_AUTHOR_EMAIL=stand@example.invalid
export GIT_COMMITTER_NAME=stand GIT_COMMITTER_EMAIL=stand@example.invalid
export GIT_CONFIG_GLOBAL=/dev/null
ok "fake gh and identity set"

# --- d. dry run
snap() { git branch; git remote; git status --porcelain; git rev-parse HEAD; cat .gitignore; }
before=$(snap)
bash scripts/publish-first.sh > "$T/dry.log" 2>&1 < /dev/null || { cat "$T/dry.log" >&2; die "dry run ended with an error"; }
[ "$before" = "$(snap)" ] || die "dry run changed branches, remote, status, HEAD or .gitignore"
ok "dry run: code 0, nothing changed"

# --- e. --go
bash scripts/publish-first.sh --go > "$T/go.log" 2>&1 < /dev/null || { cat "$T/go.log" >&2; die "--go ended with an error"; }
refs=$(git -C "$T/remote.git" for-each-ref --format='%(refname)' | sort | tr '\n' ' ')
[ "$refs" = "refs/heads/main refs/tags/v0.1.0 " ] || die "wrong refs in bare: $refs"
[ "$(git rev-list --count main)" = 1 ] || die "main has more than one commit"
block=$(git show main:.gitignore | awk '/^# single owner/{f=1;next} f&&NF&&!/^#/')
[ -n "$block" ] || die "no \"single owner\" block in .gitignore"
for p in solo-sdd docs/waiting.md $block; do
  [ -z "$(git ls-tree -r --name-only main -- "$p")" ] || die "the main tree has $p"
done
[ -z "$(git log main -- solo-sdd)" ] || die "git log main -- solo-sdd is not empty"
extra=$(git diff --name-only history-local main | grep -Ev '^(\.gitignore|solo-sdd/.*|docs/waiting\.md)$' || true)
[ -z "$extra" ] || die "main differs from history-local not only in the allowed paths: $extra"
[ -d solo-sdd ] && [ -f docs/waiting.md ] || die "solo-sdd/ or docs/waiting.md disappeared from disk"
[ -z "$(git status --porcelain)" ] || die "git status is not empty after --go"
ok "--go: one commit, main and v0.1.0 on the remote, personal files not in the tree, still on disk"

# --- f. refusals
reject() {
  local out
  if out=$("$@" 2>&1 < /dev/null); then die "the push passed but must be refused: $*"; fi
  printf '%s' "$out" | grep -q 'pre-push: refused' || die "no \"pre-push: refused\" in the output: $*"
}
reject git push origin history-local
reject git push origin history-local:refs/heads/x
reject git push origin change/old
git checkout -q -b leak main
mkdir -p solo-sdd/changes/leak
echo x > solo-sdd/changes/leak/note.md
git add -f solo-sdd/changes/leak/note.md
git commit -q -m leak
reject git push origin leak
git checkout -q main
refs=$(git -C "$T/remote.git" for-each-ref --format='%(refname)' | wc -l | tr -d ' ')
[ "$refs" = 2 ] || die "after the refusals bare does not have two refs ($refs)"
ok "the hook refused history-local, history-local:x, change/old and a commit with solo-sdd"

# --- g. CI commands in a fresh clone
git clone -q "$T/remote.git" "$T/fresh"
cmd=$(awk '/name: Run tests/{f=1;next} f&&/run: \|/{g=1;next} g{print;exit}' "$SRC/.github/workflows/test.yml" | sed 's#/usr/bin/python3#python3#g')
[ -n "$cmd" ] || die "the Run tests step not found in test.yml"
if ! (cd "$T/fresh" && bash -c "$cmd" > "$T/t.log" 2>&1); then
  tail -40 "$T/t.log" >&2
  die "CI tests failed in a fresh clone"
fi
ok "CI commands in a fresh clone: the slow tier of tests/run.py passed"
vcmd=$(awk '/name: Validate the process tree/{f=1;next} f&&/run: /{sub(/^ *run: /,""); print; exit}' "$SRC/.github/workflows/test.yml")
[ -n "$vcmd" ] || die "the Validate the process tree step not found in test.yml"
vout=$(cd "$T/fresh" && bash -c "$vcmd" 2>&1) || die "the CI validate step failed in a fresh clone without solo-sdd/: $vout"
[ "$vout" = "no solo-sdd/: nothing to check" ] || die "the CI validate step printed: $vout"
ok "CI validate step in a fresh clone without solo-sdd/: $vout"

# --- h. README on a clean home folder (no deployment to the real HOME)
mkdir -p "$T/readme" "$T/h"
python3 - "$SRC/README.md" > "$T/install.sh" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
tail = text.split("\n## Installation", 1)[1]
print(re.search(r"```bash\n(.*?)```", tail, re.S).group(1))
PY
grep -q 'https://github.com/veraetogrex-portfolio/solo-sdd' "$T/install.sh" || die "no GitHub address in the \"Installation\" block"
(cd "$T/readme" && HOME="$T/h" \
  GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0="url.$T/remote.git.insteadOf" \
  GIT_CONFIG_VALUE_0=https://github.com/veraetogrex-portfolio/solo-sdd \
  bash -eu "$T/install.sh" > "$T/readme.log" 2>&1 < /dev/null) || { tail -30 "$T/readme.log" >&2; die "the \"Installation\" block ended with an error"; }
[ -s "$T/readme.log" ] || die "the \"Installation\" block printed nothing"
# git clone prints "Cloning into" and "done.", push prints "created ..." and "all laid out", status prints "ok ...": no other lines are allowed
nok=$(grep -c '^ok ' "$T/readme.log" || true)
ncr=$(grep -c '^created ' "$T/readme.log" || true)
other=$(grep -Ev '^(ok |created |all laid out|Cloning into |done\.)' "$T/readme.log" || true)
[ -z "$other" ] || { echo "$other" >&2; die "the \"Installation\" block output has lines unlike ok"; }
{ [ "$nok" -gt 0 ] && [ "$nok" = "$ncr" ]; } || die "ok lines $nok, created $ncr: expected equal and above zero"
ok "README: install on a clean home folder, $nok ok lines"

echo "stand passed"
