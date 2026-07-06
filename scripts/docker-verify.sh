#!/usr/bin/env bash
echo "groups: $(id -nG)"
echo -n "in docker group: "; id -nG | tr ' ' '\n' | grep -qx docker && echo YES || echo NO
echo "--- docker info ---"
docker info --format 'Server={{.ServerVersion}} | containers={{.Containers}} | images={{.Images}}' 2>&1 | head -3
echo "--- docker ps ---"
docker ps 2>&1 | head -3
echo "--- python3 in WSL? (A段 pipeline 要用) ---"
command -v python3 && python3 --version || echo "python3 NOT installed"
