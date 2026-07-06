"""Pick 3 repos per scenario domain (prefer preset language + cli) -> pilot manifest."""
import json, pathlib
from collections import defaultdict

MAN = r"D:\code-bench\dataset\codegen-bench.manifest.json"
OUT = r"D:\code-bench\dataset\pilot.manifest.json"
man = json.loads(pathlib.Path(MAN).read_text(encoding="utf-8"))

PRESET = {"go", "rust", "python", "node"}
DOMAINS = ["cli_tool", "serialization_format", "web_api", "database_storage", "cryptography_security"]

by_dom = defaultdict(list)
for r in man["repos"]:
    by_dom[r["scenario"]].append(r)

picked = []
for dom in DOMAINS:
    cands = sorted(by_dom.get(dom, []), key=lambda r: (
        0 if r["language"] in PRESET else 1,     # preset language first
        0 if r["scenario_type"] == "cli" else 1,  # cli first (simplest to build)
        r["_repo"].lower()))
    picked += cands[:3]

pilot = {"dataset": "codegen-bench-pilot", "defaults": man["defaults"], "repos": picked}
pathlib.Path(OUT).write_text(json.dumps(pilot, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"picked {len(picked)} repos -> {OUT}\n")
for r in picked:
    print(f"  {r['scenario']:22} {r['scenario_type']:8} {r['language']:7} {r['_repo']}")
