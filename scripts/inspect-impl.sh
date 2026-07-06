#!/usr/bin/env bash
cd /mnt/d/code-bench/out/exam-packages/adrienverge-yamllint || exit 9
echo "=== top-level ==="; ls -1
echo "=== Dockerfile ==="; cat Dockerfile 2>/dev/null
echo "=== yamllint/ entry points ==="
ls -1 yamllint/ 2>/dev/null | head -20
[ -f yamllint/__main__.py ] && echo "  -> has yamllint/__main__.py (python -m yamllint works)"
echo "=== setup/pyproject/entry ==="; ls -1 *.py setup.* pyproject.* 2>/dev/null
echo "=== pytest in WSL? ==="; python3 -m pytest --version 2>&1 | head -1
echo "=== grader present? (112 cases) ==="; ls /mnt/d/code-bench/out/adrienverge-yamllint/07_exam/grader/cases/*.json 2>/dev/null | wc -l
echo "=== grader files ==="; ls -1 /mnt/d/code-bench/out/adrienverge-yamllint/07_exam/grader/ 2>/dev/null
