#!/usr/bin/env bash
# Fan-out the remaining 14 pilot repos (goawk is handled by the running canary).
# Disjoint repo set from the canary -> no races on out/<id>/. jobs=3 concurrent repos.
# Resumable: per-repo STATUS.json caches passed stages; a later fix re-runs only from
# the failed stage onward. Stage 0 mirrorizes each Dockerfile's FROM (Docker Hub is GFW-blocked).
export PATH="$HOME/.local/bin:$PATH"
cd /mnt/d/code-bench || exit 9
REST="achno-gowall,alexhallam-tv,alexpovel-srgn,afnanenayet-diffsitter,homeport-dyff,graphql-hive-graphql-inspector,afuh-rick-and-morty-api,anvilco-spectaql,neilotoole-sq,eralchemy-eralchemy,supabase-postgres-meta,activecm-rita-legacy,bee-san-name-that-hash,betterleaks-betterleaks"
python3 run_dataset.py --manifest dataset/pilot.manifest.json --agent codex \
    --from 0 --to 8 --jobs 3 --only "$REST" > scripts/pilot-rest.log 2>&1
echo "EXIT=$?" >> scripts/pilot-rest.log
