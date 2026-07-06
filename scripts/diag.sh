#!/usr/bin/env bash
for id in achno-gowall activecm-rita-legacy afnanenayet-diffsitter alexhallam-tv anvilco-spectaql graphql-hive-graphql-inspector; do
  echo "########## $id ##########"
  python3 - "$id" <<'PY'
import json, sys, pathlib
b = pathlib.Path(f"/mnt/d/code-bench/out/{sys.argv[1]}/00_baseline/baseline.json")
if b.exists():
    d = json.loads(b.read_text(encoding="utf-8"))
    err = d.get("docker_build_error", "(none)")
    print(err[-700:])
else:
    print("(no baseline.json)")
PY
  echo
done
echo "########## neilotoole-sq stage5 ##########"
grep -o 'PermissionError[^"]*' /mnt/d/code-bench/out/neilotoole-sq/STATUS.json 2>/dev/null | head -1
