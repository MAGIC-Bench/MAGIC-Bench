#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
echo "=== git -> github (ls-remote, no clone) ==="
if timeout 45 git ls-remote https://github.com/Achno/gowall.git HEAD >/tmp/g 2>&1; then
  echo "  OK $(cat /tmp/g)"; else echo "  FAIL"; tail -2 /tmp/g; fi
echo "=== codex CLI ==="
codex --version 2>&1 | head -1 || echo "  codex MISSING"
echo "=== codex auth (config) ==="
ls -1 ~/.codex 2>/dev/null | head -5 || echo "  no ~/.codex"
echo "=== docker daemon ==="
docker version --format 'server={{.Server.Version}}' 2>&1 | head -1
echo "=== python3 + pkgs ==="
python3 -c "import sys; print('  py', sys.version.split()[0])"
echo "=== code-bench reachable ==="
ls /mnt/d/code-bench/run_dataset.py >/dev/null 2>&1 && echo "  OK" || echo "  FAIL"
