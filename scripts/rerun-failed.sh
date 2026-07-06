#!/usr/bin/env bash
# Re-run the 9 failed pilot repos at codex reasoning_effort=xhigh, with the 3 framework
# bugs fixed (Stage 2 scenario contract, DockerRunner --user, stage8 prompt).
#  - 6 build-failure repos: drop the stale (broken) Dockerfile so xhigh codex rewrites a fresh one.
#  - 3 framework-bug repos (afuh / postgres-meta / sq): resume from their failed stage (STATUS cache).
export PATH="$HOME/.local/bin:$PATH"
cd /mnt/d/code-bench || exit 9
for id in achno-gowall activecm-rita-legacy afnanenayet-diffsitter alexhallam-tv anvilco-spectaql graphql-hive-graphql-inspector; do
  rm -f "repos/$id/Dockerfile.codebench"
done
FAILED="achno-gowall,activecm-rita-legacy,afnanenayet-diffsitter,alexhallam-tv,anvilco-spectaql,graphql-hive-graphql-inspector,afuh-rick-and-morty-api,supabase-postgres-meta,neilotoole-sq"
python3 run_dataset.py --manifest dataset/pilot.manifest.json --agent codex \
    --from 0 --to 8 --jobs 3 --only "$FAILED" > scripts/rerun-failed.log 2>&1
echo "EXIT=$?" >> scripts/rerun-failed.log
