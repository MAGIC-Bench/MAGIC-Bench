import json, pathlib
root = pathlib.Path(r"D:\code-bench-v2\dataset")
man = json.loads((root / "repo-list.manifest.json").read_text(encoding="utf-8"))
PICK = ["dosisod-refurb", "josephburnett-jd", "ogen-go-ogen", "bee-san-name-that-hash", "neilotoole-sq"]
by_id = {r["id"]: r for r in man["repos"]}
missing = [p for p in PICK if p not in by_id]
assert not missing, f"missing ids in canonical manifest: {missing}"
repos = [by_id[p] for p in PICK]
out = {"dataset": "codegen-bench-pilot-v3",
       "defaults": man.get("defaults", {"quota": 20, "runtime_mode": "docker"}),
       "repos": repos}
(root / "pilot-v3.manifest.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
print("wrote pilot-v3.manifest.json with", len(repos), "repos:")
for r in repos:
    print(f"  {r['id']:28s} | {r['scenario']:22s} | {r['scenario_type']:7s} | {r['language']:7s} | {r['source']['url']}")
