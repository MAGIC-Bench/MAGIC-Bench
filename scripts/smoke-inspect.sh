#!/usr/bin/env bash
W=/tmp/tmp.6ImZqLT3W2
echo "=== ls $W ==="
ls -la "$W" 2>&1 || echo "workspace gone"
echo "=== hello.json ==="
cat "$W/hello.json" 2>/dev/null && echo "  <<< CREATED >>>" || echo "NO hello.json"
echo "=== codex _stdout.txt (tail 40) ==="
tail -40 "$W/_stdout.txt" 2>/dev/null || echo "no _stdout.txt"
echo "=== lingering codex procs ==="
pgrep -a codex 2>/dev/null || echo "none"
