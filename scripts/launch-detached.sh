#!/usr/bin/env bash
# Launch the resume as a TRUE detached daemon (new session, no controlling terminal),
# immune to wsl-session churn from foreground polls. Unbuffered so the log fills live.
export PATH="$HOME/.local/bin:$PATH"
cd /mnt/d/code-bench || exit 9
pkill -f 'run_dataset.py' 2>/dev/null
sleep 1
REMAIN="neilotoole-sq,afuh-rick-and-morty-api,supabase-postgres-meta,activecm-rita-legacy,anvilco-spectaql,graphql-hive-graphql-inspector,afnanenayet-diffsitter"
setsid nohup env PYTHONUNBUFFERED=1 python3 -u run_dataset.py \
    --manifest dataset/pilot.manifest.json --agent codex \
    --from 0 --to 8 --jobs 1 --only "$REMAIN" \
    > scripts/rerun3.log 2>&1 < /dev/null &
disown
sleep 3
echo "launched. run_dataset pid(s): $(pgrep -f run_dataset.py | tr '\n' ' ')"
echo "rerun3.log first lines:"; head -3 scripts/rerun3.log 2>/dev/null
