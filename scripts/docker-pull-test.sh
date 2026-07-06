#!/usr/bin/env bash
pull() {
  echo "--- $1 ---"
  if timeout 150 docker pull "$1" >/tmp/p 2>&1; then echo "  OK"; else echo "  FAIL"; tail -2 /tmp/p; fi
}
pull hello-world
pull docker.m.daocloud.io/library/golang:1.22-alpine
pull docker.1ms.run/library/python:3.12-slim
pull docker.1panel.live/library/node:20-alpine
echo "--- existing images ---"
docker images --format '{{.Repository}}:{{.Tag}}'
echo "--- daemon registry-mirrors ---"
docker info 2>/dev/null | grep -A4 "Registry Mirrors" || echo "(none configured)"
