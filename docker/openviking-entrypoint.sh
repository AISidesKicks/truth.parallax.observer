#!/bin/sh
# OpenViking server entrypoint.
#
# The config file uses ${VAR} placeholders that OpenViking expands itself.
# If a variable is missing, the literal placeholder ends up as a path and the
# server quietly creates a directory with that name. Fail loudly instead.

set -eu

CONFIG="${OPENVIKING_CONFIG_FILE:-/app/openviking.conf}"

python - "$CONFIG" <<'PY'
import os
import sys

path = sys.argv[1]
raw = open(path).read()
expanded = os.path.expandvars(raw)

if "${" in expanded:
    print(f"unresolved placeholders in {path}:", file=sys.stderr)
    for line in expanded.splitlines():
        if "${" in line:
            print(f"  {line.strip()}", file=sys.stderr)
    sys.exit(1)

print(f"config ok: {path}")
PY

exec openviking-server --host 0.0.0.0 --port 1933 --config "$CONFIG"
