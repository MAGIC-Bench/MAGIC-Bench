import json, pathlib, sys
sys.path.insert(0, "/mnt/d/code-bench-v2/engine")
import nfr_security
for r in ("bee-san-name-that-hash", "neilotoole-sq", "dosisod-refurb", "ogen-go-ogen", "josephburnett-jd"):
    base = pathlib.Path("/mnt/d/code-bench-v2/out") / r
    p = base / "04_nfr-probes.json"
    print(f"=== {r} ===")
    if not p.exists():
        print("  (no 04_nfr-probes.json)")
        continue
    d = json.load(open(p, encoding="utf-8"))
    print("  implemented:", d.get("implemented"))
    has_mt = (base / "metrics-table.json").exists()
    print("  metrics-table present:", has_mt)
    print("  -> security picked:", [x["metric_id"] + ":" + x["kind"] for x in nfr_security.pick_security_metrics(base)])
