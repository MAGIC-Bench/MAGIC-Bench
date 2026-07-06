#!/usr/bin/env python3
import json
import pathlib
import sys

STATE = pathlib.Path("/mnt/yangh559/chuti-run")
GRADES = STATE / "grades"
OUT = pathlib.Path(sys.argv[1])
AGENTS = sys.argv[2].split(",") if len(sys.argv) > 2 else ["claude", "codex", "cursor", "kimi"]
EXCLUDE = {"dosisod-refurb"}

tasks = [(rid.name, agent)
         for rid in sorted(GRADES.iterdir())
         if rid.is_dir() and rid.name not in EXCLUDE
         for agent in AGENTS
         if (rid / agent / "score.json").exists()]
missing = []
for rid, agent in tasks:
    p = OUT / "case_results" / rid / agent / "summary.json"
    if not p.exists():
        missing.append((rid, agent))
print(json.dumps({"total": len(tasks), "missing": missing}, ensure_ascii=False, indent=2))
