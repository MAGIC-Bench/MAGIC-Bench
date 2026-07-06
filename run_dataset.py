"""Run the whole benchmark dataset (5 scenarios x 100 repos) through exam generation.

  python run_dataset.py --manifest dataset/manifest.json --agent claude --jobs 8
  python run_dataset.py --manifest dataset/manifest.json --only id1,id2 --from 0 --to 7

Each repo is independent (own out/<id>/, resumable via STATUS.json). Writes
out/dataset-report.json: per-repo stage reached / gate failures / per-module counts /
needs_review / high-water / mutation kill-rate.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
for _d in ("engine", "agent", "stages"):
    sys.path.insert(0, str(ROOT / _d))
sys.path.insert(0, str(ROOT))
import config as cfgmod
import orchestrate


def _summarize(out_dir) -> dict:
    out_dir = pathlib.Path(out_dir)
    rep = {}
    for name, key in [("STATUS.json", "status"), ("07_verify.json", "stage7")]:
        p = out_dir / name
        if p.exists():
            rep[key] = json.loads(p.read_text(encoding="utf-8"))
    led = out_dir / "05_coverage-ledger.json"
    if led.exists():
        rep["stage5"] = json.loads(led.read_text(encoding="utf-8"))["summary"]
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--agent", choices=["stub", "claude", "codex"], default="claude")
    ap.add_argument("--jobs", type=int, default=8)
    ap.add_argument("--from", dest="frm", type=int, default=0)
    ap.add_argument("--to", type=int, default=7)
    ap.add_argument("--only", default=None, help="comma-separated repo ids")
    args = ap.parse_args()

    manifest = cfgmod.load_manifest(args.manifest)
    configs = cfgmod.repo_configs(manifest, ROOT)
    if args.only:
        ids = set(args.only.split(","))
        configs = [c for c in configs if c["repo_id"] in ids]
    print(f"dataset={manifest.get('dataset')}  repos={len(configs)}  agent={args.agent}  jobs={args.jobs}")

    def one(c):
        try:
            ok = orchestrate.run_repo_config(c, args.agent, args.frm, args.to)
        except Exception as e:
            ok = False
            print(f"[{c['repo_id']}] ERROR {type(e).__name__}: {e}")
        return c["repo_id"], ok, _summarize(c["out_dir"])

    if args.jobs > 1 and len(configs) > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as ex:
            results = list(ex.map(one, configs))
    else:
        results = [one(c) for c in configs]

    report = {"dataset": manifest.get("dataset"), "total": len(results),
              "completed": sum(1 for _, ok, _ in results if ok),
              "repos": {rid: {"ok": ok, **summ} for rid, ok, summ in results}}
    (ROOT / "out" / "dataset-report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n=== {report['completed']}/{report['total']} repos completed ===")
    for rid, ok, summ in results:
        s5 = summ.get("stage5", {})
        nr = s5.get("needs_review", [])
        line = f"  {'OK ' if ok else 'FAIL'} {rid}"
        if s5:
            line += f" | tests={s5.get('tests_emitted')} modules_at_quota={sum(1 for v in s5.get('per_module',{}).values() if v>=s5.get('quota',20))}"
        if nr:
            line += f" | needs_review={nr}"
        print(line)
    sys.exit(0 if report["completed"] == report["total"] else 1)


if __name__ == "__main__":
    main()
