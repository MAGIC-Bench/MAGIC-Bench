#!/usr/bin/env bash
# Relaunch pilot-v2 with the new Stage-0 build-repair loop. Reset the 2 stage-0 failures
# (fresh Dockerfile + STATUS) so codex rewrites them under the new prompt + repair loop;
# carapace (already passed stage 0) resumes from stage 1; the rest run fresh.
export PATH="$HOME/.local/bin:$PATH"
cd /mnt/d/code-bench || exit 9
pkill -f run_dataset.py 2>/dev/null
sleep 1
for id in adrienverge-yamllint astral-sh-ruff; do
  rm -f "repos/$id/Dockerfile.codebench" "out/$id/STATUS.json"
done
setsid nohup env PYTHONUNBUFFERED=1 python3 -u run_dataset.py \
    --manifest dataset/pilot-v2.manifest.json --agent codex \
    --from 0 --to 8 --jobs 1 \
    > scripts/rerun-v2.log 2>&1 < /dev/null &
disown
sleep 4
echo "daemon pid: $(pgrep -f run_dataset.py | tr '\n' ' ')"
echo "log head:"; head -4 scripts/rerun-v2.log
