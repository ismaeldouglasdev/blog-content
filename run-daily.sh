#!/bin/bash
# Blog post generator - runs daily via cron

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$SCRIPT_DIR/generate.log"

echo "$(date): Starting blog post generation" >> "$LOG_FILE"

cd "$SCRIPT_DIR"
python3 generate-post.py >> "$LOG_FILE" 2>&1

echo "$(date): Finished" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"
