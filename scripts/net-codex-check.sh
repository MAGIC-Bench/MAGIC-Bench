#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
echo "=== DNS ==="
getent hosts api.openai.com | head -1 || echo "dns fail api.openai.com"
echo "=== connectivity (401 = reachable+unauth = GOOD; 000 = blocked) ==="
curl -sS -o /dev/null -w "api.openai.com/v1/models -> http_code=%{http_code} time=%{time_total}s\n" --max-time 20 https://api.openai.com/v1/models 2>&1 || echo "curl api FAILED"
curl -sS -o /dev/null -w "chatgpt.com -> http_code=%{http_code} time=%{time_total}s\n" --max-time 20 https://chatgpt.com/ 2>&1 || echo "curl chatgpt FAILED"
echo "=== codex login --help ==="
codex login --help 2>&1 | head -45
echo "=== codex doctor (status lines) ==="
timeout 45 codex doctor 2>&1 | grep -iE "auth|websocket|reachab|reset|connect failed|✓|✗|⚠" | head -25
