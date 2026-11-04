#!/bin/sh
# No external network or credentials: verify the actual image rejects defaults.
set -eu
image=${1:?Usage: tests/smoke-image.sh IMAGE}
user=$(docker image inspect "$image" --format '{{.Config.User}}')
[ "$user" = '65532:65532' ] || { echo 'Unexpected image user' >&2; exit 1; }
if output=$(docker run --rm --read-only --cap-drop ALL \
    --security-opt no-new-privileges --network none "$image" 2>&1); then
    echo 'Missing credentials unexpectedly succeeded' >&2
    exit 1
else
    status=$?
fi
[ "$status" = 1 ] || { printf '%s\n' "$output" >&2; exit 1; }
printf '%s\n' "$output" | grep -Fx 'ERROR: DUCKDNS_TOKEN is required' >/dev/null
printf '%s\n' 'Image smoke passed: non-root, read-only, isolated fail-fast startup'
