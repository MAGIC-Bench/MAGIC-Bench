#!/usr/bin/env python3
import json
import pathlib
from collections import Counter, defaultdict

BASE = pathlib.Path("/mnt/yangh559/chuti-run/grades")
AGENTS = ["claude", "codex", "cursor", "kimi"]
EXCLUDE = {"dosisod-refurb"}

out = {}
for agent in AGENTS:
    c = Counter()
    examples = defaultdict(list)
    for sp in BASE.glob(f"*/{agent}/score.json"):
        rid = sp.parts[-3]
        if rid in EXCLUDE:
            continue
        score = json.loads(sp.read_text(encoding="utf-8"))
        cmp_dim = score.get("nfr_by_dimension", {}).get("CMP", {})
        for mid in ("CMP1", "CMP2"):
            value = cmp_dim.get(mid, "MISSING")
            key = f"{mid}={repr(value)},build_ok={bool(score.get('build_ok'))}"
            c[key] += 1
            if len(examples[key]) < 4:
                examples[key].append(rid)
    out[agent] = {"counts": c, "examples": examples}

print(json.dumps(out, ensure_ascii=False, indent=2))
