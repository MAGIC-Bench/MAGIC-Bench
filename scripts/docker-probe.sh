#!/usr/bin/env bash
echo "init(pid1): $(ps -p 1 -o comm= 2>/dev/null)"
echo "--- /etc/wsl.conf ---"; cat /etc/wsl.conf 2>/dev/null || echo "(none)"
echo "docker bin: $(command -v docker)"
echo "docker version: $(docker --version 2>&1)"
echo "init.d/docker: $([ -f /etc/init.d/docker ] && echo yes || echo no)"
echo "dockerd proc: $(pgrep -a dockerd 2>/dev/null || echo none)"
echo "socket: $(ls -l /var/run/docker.sock 2>/dev/null || echo none)"
echo "user: $(id -un)  groups: $(id -nG)"
echo -n "in docker group: "; id -nG | tr ' ' '\n' | grep -qx docker && echo YES || echo NO
echo -n "sudo -n (passwordless?): "; sudo -n true 2>/dev/null && echo PASSWORDLESS || echo NEEDS_PASSWORD
echo "docker info (no sudo):"; timeout 8 docker info --format 'Server={{.ServerVersion}}' 2>&1 | head -3
