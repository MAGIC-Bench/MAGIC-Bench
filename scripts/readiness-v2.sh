#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
echo "=== git -> github (ls-remote a v2 repo) ==="
if timeout 40 git ls-remote https://github.com/astral-sh/ruff HEAD >/tmp/g 2>&1; then echo "  OK"; else echo "  FAIL"; tail -2 /tmp/g; fi
echo "=== codex ==="; codex --version 2>&1 | head -1
echo "=== docker ==="; docker version --format 'server={{.Server.Version}}' 2>&1 | head -1
echo "=== no stale run_dataset? ==="; pgrep -f run_dataset.py >/dev/null && echo "  WARNING: a run_dataset is already running" || echo "  clean (none running)"
echo "=== pilot-v2 manifest ==="
python3 -c "import json;d=json.load(open('/mnt/d/code-bench/dataset/pilot-v2.manifest.json'));print('  repos:',len(d['repos']));[print('   ',r['id'],r['scenario_type'],r['language']) for r in d['repos']]"
echo "=== free mem ==="; free -h | awk 'NR==2{print "  available:",$7}'
