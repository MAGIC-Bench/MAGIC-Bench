import json, pathlib, sys
sys.path.insert(0, "/mnt/d/code-bench-v2/engine")
import gates
base = pathlib.Path("/mnt/d/code-bench-v2/out/neilotoole-sq")
tests = sorted((base / "05_tests").glob("*.json"))
print("05_tests count:", len(tests))

# content coverage now (post my gate fix)
print("content_coverage_ratio:", gates._content_coverage_ratio(base))

# assertion class histogram across all cases
from collections import Counter
cls_hist, field_hist = Counter(), Counter()
for t in tests:
    c = json.loads(t.read_text(encoding="utf-8"))
    for a in c.get("assertions", []):
        cls_hist[a.get("class")] += 1
        field_hist[str(a.get("field"))[:12]] += 1
print("assertion classes:", dict(cls_hist))
print("assertion fields:", dict(field_hist))

# show 3 sample cases
for t in tests[:3]:
    c = json.loads(t.read_text(encoding="utf-8"))
    print("---", c["id"], "| argv:", (c.get("input", {}).get("argv")))
    print("   assertions:", [{k: a.get(k) for k in ("field", "class", "rule")} for a in c.get("assertions", [])])

adv = json.loads((base / "06_adversarial.json").read_text(encoding="utf-8"))
print("=== 06_adversarial ===")
print("open_critical:", adv.get("open_critical"), "repair_attempts:", adv.get("repair_attempts"))
fs = adv.get("findings", [])
print("findings:", len(fs))
for f in fs[:14]:
    print("  -", (f.get("severity") or "?"), "|", str(f.get("test_id") or "")[:40], "|", str(f.get("issue", ""))[:80])
