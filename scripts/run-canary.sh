#!/usr/bin/env bash
export PATH="$HOME/.local/bin:$PATH"
cd /mnt/d/code-bench || exit 9
python3 run_dataset.py --manifest dataset/pilot.manifest.json --agent codex \
    --from 0 --to 8 --jobs 1 --only benhoyt-goawk > scripts/canary-goawk.log 2>&1
echo "EXIT=$?" >> scripts/canary-goawk.log
