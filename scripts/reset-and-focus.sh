#!/usr/bin/env bash
# Clean slate + refocus: the count is stuck because (a) manifest order runs doomed build-repos
# first, and (b) orphaned builds from the dead runs hog memory. Kill everything, then relaunch
# detached on ONLY the 3 high-confidence framework-bug repos (afuh / sq / postgres-meta).
export PATH="$HOME/.local/bin:$PATH"
cd /mnt/d/code-bench || exit 9

echo "killing daemon + orphan builds ..."
pkill -9 -f 'run_dataset.py' 2>/dev/null
pkill -9 -f 'codex exec'     2>/dev/null
pkill -9 -x cargo            2>/dev/null
pkill -9 -f 'pnpm'           2>/dev/null
pkill -9 -f 'yarn'           2>/dev/null
pkill -9 -f 'go build'       2>/dev/null
docker ps -q 2>/dev/null | xargs -r docker kill 2>/dev/null >/dev/null
sleep 3
echo "  remaining build procs: $(pgrep -c -E 'cargo|pnpm|yarn|go build' 2>/dev/null || echo 0)"
echo "  free mem: $(free -h | awk 'NR==2{print $7}') available"

FOCUS="afuh-rick-and-morty-api,neilotoole-sq,supabase-postgres-meta"
setsid nohup env PYTHONUNBUFFERED=1 python3 -u run_dataset.py \
    --manifest dataset/pilot.manifest.json --agent codex \
    --from 0 --to 8 --jobs 1 --only "$FOCUS" \
    > scripts/rerun4.log 2>&1 < /dev/null &
disown
sleep 4
echo "daemon pid: $(pgrep -f run_dataset.py | tr '\n' ' ')"
echo "log:"; head -4 scripts/rerun4.log
