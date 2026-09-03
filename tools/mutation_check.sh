#!/usr/bin/env bash
# mutation_check.sh — verify that the oracle actually catches the bug.
#
#   bash tools/mutation_check.sh
#
# The README argues that a suite reading only the API cannot see a stale cache,
# and that a second source can. That argument is only worth anything if it still
# holds. So this script breaks the service on purpose and checks that the right
# test, and only the right test, notices.
#
# It removes the eviction call from demo/app.py, rebuilds the service, and
# expects:
#
#   tests/demo/test_design_techniques.py   all pass   (blind to the bug)
#   tests/demo/test_oracles.py             1 failure  (the cache oracle)
#
# A green run here means the oracle is load-bearing. If the oracle suite passes
# with the eviction gone, the oracle has stopped testing anything and this
# script fails the build. That is the failure mode a response-only suite cannot
# report about itself, which is the whole point of the repository.
#
# The mutation is reverted on exit, including on failure and on interrupt.
set -uo pipefail

cd "$(git rev-parse --show-toplevel)" || exit 2

COMPOSE="docker compose -f demo/docker-compose.yml"
APP="demo/app.py"
EVICTION='_redis.delete(cache_key(order_id))'
BACKUP="$(mktemp)"

restore() {
  if [ -f "$BACKUP" ]; then
    cp "$BACKUP" "$APP"
    rm -f "$BACKUP"
    printf '\n-- reverted %s --\n' "$APP"
  fi
}
trap restore EXIT INT TERM

# --- apply the mutation ----------------------------------------------------
cp "$APP" "$BACKUP"

hits=$(grep -c -F "$EVICTION" "$APP")
if [ "$hits" -ne 1 ]; then
  echo "!! expected exactly one eviction call in $APP, found $hits"
  echo "   The mutation target moved. Update EVICTION in this script rather"
  echo "   than deleting the check."
  exit 1
fi

# Replace the call with a no-op, keeping the line count stable so tracebacks
# from the mutated run still line up with the real file.
python3 - "$APP" "$EVICTION" <<'PY'
import sys
path, target = sys.argv[1], sys.argv[2]
src = open(path).read()
out = src.replace(target, "pass  # mutation_check.sh: eviction removed", 1)
assert out != src, "mutation did not apply"
open(path, "w").write(out)
PY

echo "== mutation applied: cache eviction removed =="

# --- rebuild and wait ------------------------------------------------------
$COMPOSE up -d --build api || exit 1

for _ in $(seq 1 30); do
  if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then break; fi
  sleep 2
done
curl -fsS http://localhost:8000/health >/dev/null || {
  echo "!! demo service did not come up"
  exit 1
}

# --- the two expectations --------------------------------------------------
fail=0

echo
echo "== response-layer tests should be blind to this =="
if pytest tests/demo/test_design_techniques.py -q; then
  echo "OK: the API-only suite still passes, as the argument predicts"
else
  fail=1
  echo "!! the API-only suite failed. Either the mutation broke more than the"
  echo "   cache, or a test in that file has quietly grown a second source."
fi

echo
echo "== the cache oracle should catch it =="
pytest tests/demo/test_oracles.py -q
rc=$?
# pytest exits 1 when tests failed, which is what we want here.
if [ "$rc" -eq 1 ]; then
  echo "OK: the oracle suite failed, as it must"
elif [ "$rc" -eq 0 ]; then
  fail=1
  echo "!! the oracle suite PASSED with cache eviction removed."
  echo "   The oracle is no longer testing anything. This is the exact failure"
  echo "   the README claims this repository exists to make visible."
else
  fail=1
  echo "!! the oracle suite exited $rc, which is neither pass nor test failure"
fi

echo
echo "========== RESULT =========="
if [ "$fail" -eq 0 ]; then
  echo "✓ mutation check PASSED — the oracle is load-bearing"
else
  echo "✗ mutation check FAILED — see above"
fi
exit "$fail"
