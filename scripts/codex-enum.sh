#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
timeout 25 codex exec -c model_reasoning_effort=zzz --skip-git-repo-check "noop" 2>&1 | head -30
echo "rc=${PIPESTATUS[0]}"
