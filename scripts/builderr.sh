#!/usr/bin/env bash
for id in achno-gowall activecm-rita-legacy afnanenayet-diffsitter alexhallam-tv anvilco-spectaql graphql-hive-graphql-inspector; do
  echo "###################### $id ######################"
  echo "----- Dockerfile.codebench (FROM + RUN lines) -----"
  grep -nE '^\s*(FROM|RUN|ARG|WORKDIR|ENTRYPOINT)' "/mnt/d/code-bench/repos/$id/Dockerfile.codebench" 2>/dev/null | cut -c1-200
  echo "----- full docker_build_error tail -----"
  python3 - "$id" <<'PY'
import json, sys, pathlib
b = pathlib.Path(f"/mnt/d/code-bench/out/{sys.argv[1]}/00_baseline/baseline.json")
if b.exists():
    d = json.loads(b.read_text(encoding="utf-8"))
    print((d.get("docker_build_error") or "(none)")[-1400:])
else:
    print("(no baseline.json)")
PY
  echo
done
