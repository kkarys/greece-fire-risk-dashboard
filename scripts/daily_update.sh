#!/bin/bash
# Daily update: fetch any new fire-risk maps, extract risk levels, and push
# the updated dataset so the deployed Streamlit Cloud app picks it up.
#
# Re-fetches the last 5 days (not just "today") so a missed run (e.g. laptop
# asleep) is caught up automatically. Both the scraper and pipeline are
# idempotent, so re-running over already-downloaded/processed dates is a no-op.

set -euo pipefail

PROJECT_DIR="/Users/iti-thermi/Documents/SideProject"
PYTHON="/usr/bin/python3"
LOG_FILE="$PROJECT_DIR/data/daily_update.log"

cd "$PROJECT_DIR"

START_DATE=$(date -v-5d +%Y-%m-%d)
END_DATE=$(date +%Y-%m-%d)

{
  echo "=== Daily update run: $(date) ==="

  "$PYTHON" src/scraper.py "$START_DATE" "$END_DATE"
  "$PYTHON" src/pipeline.py

  if ! git diff --quiet -- data/raw data/processed; then
    git add data/raw data/processed
    git commit -m "Daily update: maps through $END_DATE"
    git push origin main
    echo "Pushed updates through $END_DATE"
  else
    echo "No new data to commit"
  fi

  echo "=== Done: $(date) ==="
  echo
} >> "$LOG_FILE" 2>&1
