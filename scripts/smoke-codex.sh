#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
echo "=== codex login status ==="
codex login status
echo "=== doctor (status lines) ==="
timeout 60 codex doctor 2>&1 | grep -iE "auth|reachab|websocket| ok |✓|✗|⚠" | head -14
echo
echo "=== SMOKE: codex exec writes a file (the core --agent codex mechanism) ==="
SMK=$(mktemp -d)
echo "workspace: $SMK"
timeout 240 codex exec 'Create a file named hello.json in the current working directory whose exact content is the single line: {"ok": true, "agent": "codex"}  -- then stop. Do not print anything else.' \
  --cd "$SMK" --sandbox workspace-write --skip-git-repo-check --color never \
  > "$SMK/_stdout.txt" 2>&1
echo "codex exec exit=$?"
echo "--- workspace files ---"
ls -la "$SMK"
echo "--- hello.json ---"
cat "$SMK/hello.json" 2>/dev/null && echo "  <<< FILE CREATED OK >>>" || echo "  hello.json NOT created"
echo "--- codex stdout (tail 12) ---"
tail -12 "$SMK/_stdout.txt"
