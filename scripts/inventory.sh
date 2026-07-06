#!/usr/bin/env bash
cd /mnt/d/code-bench || exit 9
echo "=== root entry points ==="
wc -l orchestrate.py run_dataset.py run_repo.py run_candidate.py chuti.py 2>/dev/null | grep -v ' total'
echo "=== engine/ ==="
wc -l engine/*.py 2>/dev/null | grep -v ' total'
echo "=== stages/ ==="
wc -l stages/*.py 2>/dev/null | grep -v ' total'
echo "=== agent/ ==="
wc -l agent/*.py 2>/dev/null | grep -v ' total'
echo "=== TOTAL framework .py lines ==="
cat orchestrate.py run_dataset.py run_repo.py run_candidate.py chuti.py engine/*.py stages/*.py agent/*.py 2>/dev/null | wc -l
echo "=== prompts/ (markdown instructions, not code) ==="
ls -1 prompts/ 2>/dev/null
echo "=== schemas/ (json) ==="
ls -1 schemas/ 2>/dev/null
echo "=== docker/ (reference Dockerfile templates) ==="
ls -1 docker/ 2>/dev/null
