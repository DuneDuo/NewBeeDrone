#!/bin/bash
# Stop hook — fires when Claude session ends (window close, /clear, compact, etc.)
# Writes a session-end marker so the next session knows where we left off.

MEMORY_DIR="$(cygpath -u "$HOME/.claude/projects/C--Users-DouDou-Desktop---/memory" 2>/dev/null || echo "$HOME/.claude/projects/C--Users-DouDou-Desktop---/memory")"
mkdir -p "$MEMORY_DIR"

# Read stdin JSON to get session_id (capture all input first)
SESSION_ID="unknown"
STDIN_DATA=$(cat 2>/dev/null)
if [ -n "$STDIN_DATA" ]; then
  SID=$(echo "$STDIN_DATA" | grep -o '"session_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/')
  [ -n "$SID" ] && SESSION_ID="$SID"
fi

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
echo "$TIMESTAMP|$SESSION_ID" > "$MEMORY_DIR/_last-session.txt"

exit 0
