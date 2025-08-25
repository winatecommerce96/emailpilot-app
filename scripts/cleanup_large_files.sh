#!/usr/bin/env bash
set -euo pipefail

THRESHOLD="500M"
MODE="list"  # list|delete|truncate
YES="no"

usage() {
  cat <<EOF
Usage: $0 [-t SIZE] [--delete|--truncate] [--yes]

Find large files and optionally delete or truncate them.

Options:
  -t SIZE        Threshold (default: 500M). Examples: 200M, 1G
  --delete       Delete matching files (prompt unless --yes)
  --truncate     Truncate matching files to zero bytes (prompt unless --yes)
  --yes          Do not prompt for confirmation

Notes:
  - Targets files larger than SIZE and common log patterns: *.log, *.out, logs/*
  - Always review before destructive actions.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -t)
      THRESHOLD="$2"; shift 2;;
    --delete)
      MODE="delete"; shift;;
    --truncate)
      MODE="truncate"; shift;;
    --yes)
      YES="yes"; shift;;
    -h|--help)
      usage; exit 0;;
    *)
      echo "Unknown option: $1" >&2; usage; exit 1;;
  esac
done

echo "Scanning for files > $THRESHOLD (logs and .out/.log)…"

# Build candidate list: large files; prioritize *.log/*.out and logs/
mapfile -t FILES < <(\
  find . -type f \( -name "*.log" -o -name "*.out" -o -path "./logs/*" \) -size +"$THRESHOLD" -print 2>/dev/null
)

if [[ ${#FILES[@]} -eq 0 ]]; then
  echo "No files over $THRESHOLD matched log patterns."
  exit 0
fi

echo "Found ${#FILES[@]} large file(s):"
ls -lh "${FILES[@]}" 2>/dev/null || true

case "$MODE" in
  list)
    echo "(list mode) No changes made."
    ;;
  delete|truncate)
    if [[ "$YES" != "yes" ]]; then
      read -r -p "Proceed to $MODE these files? [y/N] " ans
      [[ "$ans" == "y" || "$ans" == "Y" ]] || { echo "Aborted."; exit 1; }
    fi
    for f in "${FILES[@]}"; do
      if [[ "$MODE" == "delete" ]]; then
        rm -f -- "$f" && echo "Deleted: $f" || echo "Failed: $f"
      else
        : > "$f" && echo "Truncated: $f" || echo "Failed: $f"
      fi
    done
    ;;
esac

echo "Done."

