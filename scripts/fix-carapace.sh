#!/usr/bin/env bash
# Re-run carapace with the resume fix: _merge_runtime now fires on resume -> coverage='none' ->
# stage7 skips the gron-specific mutation path -> high-water only -> pass -> stage8 package.
# Disjoint from the main jobs=2 daemon (which already failed+left carapace). Stage 7-8 = no codex, cheap.
export PATH="$HOME/.local/bin:$PATH"
cd /mnt/d/code-bench || exit 9
setsid nohup env PYTHONUNBUFFERED=1 python3 -u run_dataset.py \
    --manifest dataset/pilot-v2.manifest.json --agent codex \
    --from 0 --to 8 --jobs 1 --only carapace-sh-carapace-bin \
    > scripts/carapace-fix.log 2>&1 < /dev/null &
disown
sleep 5
echo "log:"; cat scripts/carapace-fix.log
