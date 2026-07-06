#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
PKG=/mnt/d/code-bench/out/exam-packages/blst-security-cherrybomb
GRADER=/mnt/d/code-bench/out/blst-security-cherrybomb/07_exam/grader
echo "### go.mod ###"; cat "$PKG/go.mod"
echo "### base golang:1.22-alpine (Docker Hub blocked -> mirror+tag) ###"
if ! docker image inspect golang:1.22-alpine >/dev/null 2>&1; then
  docker pull docker.m.daocloud.io/library/golang:1.22-alpine && docker tag docker.m.daocloud.io/library/golang:1.22-alpine golang:1.22-alpine
fi
echo "  ready"
python3 /mnt/d/code-bench/scripts/inject_goproxy.py "$PKG"
echo "### build cand-cherrybomb ###"
docker build -t cand-cherrybomb -f "$PKG/Dockerfile.grade" "$PKG" 2>&1 | tail -8 || { echo BUILD_FAILED; exit 1; }
echo "### GRADE (59 cases via docker) ###"
cd "$GRADER" || exit 9
CANDIDATE_IMAGE=cand-cherrybomb python3 -m pytest -q -p no:cacheprovider 2>&1 | tail -45
