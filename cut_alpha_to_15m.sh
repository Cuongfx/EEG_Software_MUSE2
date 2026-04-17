#!/usr/bin/env bash

set -euo pipefail

INPUT="${1:-alpha.mp3}"
OUTPUT="${2:-alpha_15m.mp3}"
DURATION_SECONDS=900

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "Error: ffmpeg is not installed or not in PATH." >&2
  exit 1
fi

if [[ ! -f "$INPUT" ]]; then
  echo "Error: input file '$INPUT' was not found." >&2
  exit 1
fi

ffmpeg -y -i "$INPUT" -t "$DURATION_SECONDS" -c copy "$OUTPUT"

echo "Created '$OUTPUT' from '$INPUT' with duration capped at 15 minutes."
