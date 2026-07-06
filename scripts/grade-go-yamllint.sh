#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
PKG='/mnt/d/code-bench/out/exports/yamllint-AGENT-题面-给agent'
GRADER='/mnt/d/code-bench/out/adrienverge-yamllint/07_exam/grader'   # canonical, 111 fair cases
echo "### go.mod ###"; cat "$PKG/go.mod"
echo "### base golang:1.24-alpine (Docker Hub blocked -> mirror+tag) ###"
if ! docker image inspect golang:1.24-alpine >/dev/null 2>&1; then
  docker pull docker.m.daocloud.io/library/golang:1.24-alpine && docker tag docker.m.daocloud.io/library/golang:1.24-alpine golang:1.24-alpine
fi
echo "  ready"
python3 /mnt/d/code-bench/scripts/inject_goproxy.py "$PKG"
echo "### build cand-yamllint-go ###"
docker build -t cand-yamllint-go -f "$PKG/Dockerfile.grade" "$PKG" 2>&1 | tail -8 || { echo BUILD_FAILED; exit 1; }
echo "### GRADE (yamllint, 111 cases via docker) ###"
cd "$GRADER" || exit 9
CANDIDATE_IMAGE=cand-yamllint-go python3 -m pytest -q -p no:cacheprovider 2>&1 | tail -55
