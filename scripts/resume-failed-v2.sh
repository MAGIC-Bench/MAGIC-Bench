#!/usr/bin/env bash
# Smart resume of the 3 failed pilot-v2 repos:
#  - dinedal-textql: fixed Dockerfile already written (HTTP apt mirror) -> stage0 rebuilds, should pass
#  - schemacrawler: clone died on GnuTLS reset (GFW) -> harden git + re-clone fresh
#  - evgskv-logica: stage5 fail (diagnosis agent died) -> retry from stage5
export PATH="$HOME/.local/bin:$PATH"
cd /mnt/d/code-bench || exit 9
git config --global http.version HTTP/1.1          # mitigate GnuTLS connection-reset on github clone
git config --global http.postBuffer 524288000
rm -rf repos/schemacrawler-schemacrawler           # clean any partial clone so stage0 re-clones fresh
pkill -f run_dataset.py 2>/dev/null
sleep 1
FAILED="dinedal-textql,schemacrawler-schemacrawler,evgskv-logica"
setsid nohup env PYTHONUNBUFFERED=1 python3 -u run_dataset.py \
    --manifest dataset/pilot-v2.manifest.json --agent codex \
    --from 0 --to 8 --jobs 2 --only "$FAILED" \
    > scripts/resume-v2.log 2>&1 < /dev/null &
disown
sleep 4
echo "resume pid: $(pgrep -f run_dataset.py | tr '\n' ' ')"
echo "log:"; head -5 scripts/resume-v2.log
