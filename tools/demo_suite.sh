#!/usr/bin/env bash
# demo_suite.sh — run the demo suite against a live stack, and refuse to skip.
#
#   bash tools/demo_suite.sh
#
# tests/demo skips itself when the stack is not running. On a laptop that is the
# right behaviour: a red suite should mean the service is wrong, not that you
# forgot to run docker.
#
# On CI it is the wrong behaviour, and it hid something for two weeks. Docker is
# available on the runner, so nobody forgot anything, and the skip turned "the
# stack was never started" into a green badge. Every run reported
# "19 passed, 50 skipped" while the entire demo suite, including the one oracle
# test the README's argument rests on, had never executed.
#
# So this script brings the stack up itself and then treats any skip as a
# failure. A badge is binary. It cannot show the difference between 0 skipped
# and 50 skipped, so the difference has to be enforced here.
set -uo pipefail

cd "$(git rev-parse --show-toplevel)" || exit 2

COMPOSE="docker compose -f demo/docker-compose.yml"

$COMPOSE up -d --build || exit 1

for _ in $(seq 1 30); do
  if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then break; fi
  sleep 2
done
curl -fsS http://localhost:8000/health >/dev/null || {
  echo "!! demo service did not come up; the suite would have skipped silently"
  $COMPOSE logs --tail 50 api
  exit 1
}

# -p no:cacheprovider keeps a .pytest_cache out of the runner's workspace.
pytest tests/demo -q -rs -p no:cacheprovider \
  --junit-xml=demo-results.xml
rc=$?

if [ "$rc" -ne 0 ]; then
  echo "!! demo suite failed"
  exit "$rc"
fi

# The suite passed. Now check that it actually ran.
python3 - demo-results.xml <<'PY' || exit 1
import sys, xml.etree.ElementTree as ET

root = ET.parse(sys.argv[1]).getroot()
suite = root.find("testsuite") if root.tag == "testsuites" else root

tests = int(suite.get("tests", 0))
skipped = int(suite.get("skipped", 0))
ran = tests - skipped

print(f"\ncollected {tests}, skipped {skipped}, ran {ran}")

if skipped:
    print(
        f"!! {skipped} test(s) skipped. On CI the stack is up, so a skip here "
        "means the suite silently did not run. Failing rather than reporting "
        "green on tests that never executed."
    )
    sys.exit(1)

if ran == 0:
    print("!! nothing ran")
    sys.exit(1)

print(f"OK: all {ran} demo tests executed against the live stack")
PY
