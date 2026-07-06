#!/usr/bin/env bash
# Probe the WSL substrate the pilot needs: docker daemon, codex, go/python, proxies, repos dir.
echo "=== uname ==="; uname -a
echo "=== docker daemon ==="; docker info >/dev/null 2>&1 && echo "DOCKER_UP" || echo "DOCKER_DOWN"
echo "=== docker version ==="; docker --version 2>/dev/null || echo "no docker"
echo "=== codex ==="; command -v codex || echo "NO codex on PATH"
echo "=== go ==="; command -v go && go env GOPROXY 2>/dev/null
echo "=== python3 ==="; command -v python3
echo "=== git ==="; command -v git
echo "=== code-bench-v2 mount ==="; ls -d /mnt/d/code-bench-v2 2>/dev/null && echo OK || echo "NO mount"
echo "=== repos dir ==="; ls -1 /mnt/d/code-bench-v2/repos 2>/dev/null | head -5; echo "(count: $(ls /mnt/d/code-bench-v2/repos 2>/dev/null | wc -l))"
echo "=== free mem ==="; free -h 2>/dev/null | head -2
echo "=== pip mirror ==="; (pip config list 2>/dev/null | grep -i index) || echo "(no pip index config)"
