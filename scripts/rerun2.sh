#!/usr/bin/env bash
# Resume after the jobs=3 run died (likely OOM: 3x xhigh codex + parallel heavy builds on a 7.6GB VM).
# jobs=1 (serial) -> peak load = one codex OR one build at a time, can't re-OOM. gowall+tv already DONE
# (0-8) so excluded. Order front-loads the high-confidence repos; diffsitter (slow rust build) last.
export PATH="$HOME/.local/bin:$PATH"
cd /mnt/d/code-bench || exit 9
pkill -f 'run_dataset.py' 2>/dev/null
sleep 2
REMAIN="neilotoole-sq,afuh-rick-and-morty-api,supabase-postgres-meta,activecm-rita-legacy,anvilco-spectaql,graphql-hive-graphql-inspector,afnanenayet-diffsitter"
python3 run_dataset.py --manifest dataset/pilot.manifest.json --agent codex \
    --from 0 --to 8 --jobs 1 --only "$REMAIN" > scripts/rerun2.log 2>&1
echo "EXIT=$?" >> scripts/rerun2.log
