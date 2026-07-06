#!/usr/bin/env python3
import json
import pathlib
from collections import Counter, defaultdict

BASE = pathlib.Path("/mnt/yangh559/chuti-run/grades")
AGENTS = {"claude", "codex", "cursor", "kimi"}
EXCLUDE = {"dosisod-refurb"}

counts = Counter()
counts_by_build = Counter()
examples = defaultdict(list)
for sp in BASE.glob("*/*/score.json"):
    rid = sp.parts[-3]
    agent = sp.parts[-2]
    if rid in EXCLUDE or agent not in AGENTS:
        continue
    score = json.loads(sp.read_text(encoding="utf-8"))
    value = score.get("nfr_by_dimension", {}).get("CMP", {}).get("CMP2", "MISSING")
    key = repr(value)
    counts[key] += 1
    counts_by_build[(str(bool(score.get("build_ok"))), key)] += 1
    if len(examples[key]) < 8:
        examples[key].append(f"{rid}/{agent}")

print(json.dumps({
    "counts": counts,
    "counts_by_build_ok": {f"build_ok={b}, CMP2={k}": v for (b, k), v in counts_by_build.items()},
    "examples": examples,
}, ensure_ascii=False, indent=2))
