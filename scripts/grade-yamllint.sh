#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
PKG=/mnt/d/code-bench/out/exam-packages/adrienverge-yamllint
GRADER=/mnt/d/code-bench/out/adrienverge-yamllint/07_exam/grader

echo "### 1. pytest ###"
if ! python3 -c "import pytest" 2>/dev/null; then
  python3 -m pip install --break-system-packages -q -i https://pypi.tuna.tsinghua.edu.cn/simple pytest 2>&1 | tail -3
fi
python3 -c "import pytest; print('  pytest', pytest.__version__)" || { echo "pytest install FAILED"; exit 1; }

echo "### 2. base image (Docker Hub blocked -> mirror + tag) ###"
if ! docker image inspect python:3.12-slim >/dev/null 2>&1; then
  docker pull docker.m.daocloud.io/library/python:3.12-slim && docker tag docker.m.daocloud.io/library/python:3.12-slim python:3.12-slim
fi
echo "  python:3.12-slim ready"

echo "### 3. build candidate image ###"
docker build -t cand-yamllint "$PKG" 2>&1 | tail -4 || { echo "BUILD FAILED"; exit 1; }

echo "### 4. GRADE (112 cases via docker) ###"
cd "$GRADER" || exit 9
CANDIDATE_IMAGE=cand-yamllint python3 -m pytest -q -p no:cacheprovider 2>&1 | tail -50
