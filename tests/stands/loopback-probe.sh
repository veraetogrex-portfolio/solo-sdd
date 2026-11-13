#!/usr/bin/env bash
# Live Scenario stand of change dispatch-loopback-probe, steps 1-2, on sdd_dispatch_plan.py of this checkout.
# Its own project with one stub change in a temporary folder, removed on exit.
# Step 1: the plan in this session; if the session itself has no loopback, the probe of the same script
# in a local container with --network none (it has its own loopback; files go through stdin).
# Step 2: the plan under a sandbox that denies network (sandbox-exec on macOS, unshare -rn on Linux),
# without and with the item «Loopback: needed» in AGENTS.md.
# Run from the repository root: bash tests/stands/loopback-probe.sh
set -uo pipefail

SCRIPT="$(cd "$(dirname "$0")/../.." && pwd)/global/sdd_dispatch_plan.py"
IMAGE="python:3.12-slim-bookworm"
DIR="$(mktemp -d "${TMPDIR:-/tmp}/loopback-probe-XXXXXX")"
trap 'rm -rf "$DIR"' EXIT
PASS=0
FAIL=0
check() {
  if [ "$1" = 0 ]; then PASS=$((PASS + 1)); echo "PASS $2"; else FAIL=$((FAIL + 1)); echo "FAIL $2"; fi
}

git init -q -b main "$DIR/project"
mkdir -p "$DIR/project/openspec/changes/a"
printf '# a\n\n## Depends On\n\nnone\n' > "$DIR/project/openspec/changes/a/proposal.md"
git -C "$DIR/project" add -A
git -C "$DIR/project" -c user.name=t -c user.email=t@t commit -qm init

OUT="$(python3 "$SCRIPT" "$DIR/project" < /dev/null)"
CODE=$?
LINE="$(printf '%s\n' "$OUT" | sed -n 2p)"
echo "step 1 session: code $CODE, $LINE"
if [ "$LINE" = "loopback: ok" ]; then
  check 0 "step 1: the session prints loopback: ok"
elif command -v docker > /dev/null && docker image inspect "$IMAGE" > /dev/null 2>&1; then
  BOX="$(docker run --rm -i --network none "$IMAGE" python3 -c \
    "import sys; ns = {'__name__': 'probe'}; exec(sys.stdin.read(), ns); print('loopback: ' + ns['loopback']())" \
    < "$SCRIPT" 2>&1)"
  echo "step 1 container: $BOX"
  [ "$BOX" = "loopback: ok" ]
  check $? "step 1: the session has no loopback ($LINE); the same probe in a container prints loopback: ok"
else
  check 1 "step 1: the session has no loopback ($LINE) and no local image $IMAGE to show loopback: ok"
fi

case "$(uname)" in
  Darwin) BOXED=(sandbox-exec -p '(version 1)(allow default)(deny network*)') ;;
  *) BOXED=(unshare -rn) ;;
esac
SOUT="$("${BOXED[@]}" python3 "$SCRIPT" "$DIR/project" < /dev/null)"
SCODE=$?
SLINE="$(printf '%s\n' "$SOUT" | sed -n 2p)"
echo "step 2 sandbox: code $SCODE, $SLINE"
case "$SLINE" in
  "loopback: blocked: "?*) check 0 "step 2: the sandbox prints loopback: blocked: <error>" ;;
  *) check 1 "step 2: the sandbox prints loopback: blocked: <error>" ;;
esac
[ "$SCODE" = "$CODE" ]
check $? "step 2: the exit code is unchanged ($SCODE)"
[ "$(printf '%s\n' "$SOUT" | sed 2d)" = "$(printf '%s\n' "$OUT" | sed 2d)" ]
check $? "step 2: the rest of the plan is the same: $(printf '%s\n' "$SOUT" | sed 2d | tr '\n' '|')"

printf '# p\n\n## Commands\n\n- Loopback: needed\n' > "$DIR/project/AGENTS.md"
NLINE="$("${BOXED[@]}" python3 "$SCRIPT" "$DIR/project" < /dev/null | sed -n 2p)"
echo "step 2 sandbox, AGENTS.md declares the need: $NLINE"
case "$NLINE" in
  "loopback: blocked (needed by the project): "?*) check 0 "step 2: a declared need marks the block" ;;
  *) check 1 "step 2: a declared need marks the block" ;;
esac

echo "loopback-probe stand: $PASS of $((PASS + FAIL)) checks passed"
[ "$FAIL" = 0 ]
