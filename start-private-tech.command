#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Install Python 3 from python.org, then run this launcher again."
  exit 1
fi
printf '%s\n' 'Personal tech dashboard: http://127.0.0.1:8765' 'Keep this terminal open. Press Control+C to stop.'
exec python3 ozwatch.py --loop 900 --serve
