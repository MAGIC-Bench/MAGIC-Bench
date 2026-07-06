#!/usr/bin/env bash
# Fan-out: run the full 15-repo pilot through Stage 0-8 in docker mode.
# goawk (the canary) already has STATUS pass for its stages -> they skip instantly (resumable).
# jobs=3: at most 3 concurrent repos (3 concurrent codex + up to 3 docker builds).
export PATH="$HOME/.local/bin:$PATH"
cd /mnt/d/code-bench || exit 9
python3 run_dataset.py --manifest dataset/pilot.manifest.json --agent codex \
    --from 0 --to 8 --jobs 3 > scripts/pilot-all.log 2>&1
echo "EXIT=$?" >> scripts/pilot-all.log
