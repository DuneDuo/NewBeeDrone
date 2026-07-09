#!/bin/bash
# SessionStart hook — fired when Claude session starts.
# If a previous session marker exists, injects context so Claude reviews memory.

MEMORY_DIR="$(cygpath -u "$HOME/.claude/projects/C--Users-DouDou-Desktop---/memory" 2>/dev/null || echo "$HOME/.claude/projects/C--Users-DouDou-Desktop---/memory")"
MARKER="$MEMORY_DIR/_last-session.txt"

if [ -f "$MARKER" ]; then
  LAST_LINE=$(tail -1 "$MARKER")
  LAST_TIME=$(echo "$LAST_LINE" | cut -d'|' -f1)

  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"上次会话结束于 %s。请简要回顾记忆文件，将上轮对话中的关键进展、决策、代码变更写入对应记忆文件（项目目录 \\`CLAUDE.md\\` 和 memory 目录）。"}}' "$LAST_TIME"

  rm -f "$MARKER"
fi

exit 0
