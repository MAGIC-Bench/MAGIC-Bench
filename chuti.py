"""Top-level CLI for the exam-generation pipeline.

  python chuti.py --repo gron                 # one repo, stages 0-7
  python chuti.py --repo gron --agent claude  # use headless Claude for the model stages
  python chuti.py --all                        # every configs/*.json (skip _*.json)
  python chuti.py --all --jobs 4               # in parallel
  python chuti.py --repo gron --from 5 --to 7  # re-run a stage range
"""
from __future__ import annotations

import argparse
import concurrent.futures
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import orchestrate


def discover_repos():
    return sorted(p.stem for p in (ROOT / "configs").glob("*.json") if not p.name.startswith("_"))


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--repo")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--agent", choices=["stub", "claude", "codex"], default="stub")
    ap.add_argument("--from", dest="frm", type=int, default=0)
    ap.add_argument("--to", type=int, default=7)
    ap.add_argument("--jobs", type=int, default=8)
    args = ap.parse_args()

    repos = discover_repos() if args.all else [args.repo]
    print(f"repos: {repos}  agent={args.agent}  stages {args.frm}..{args.to}")

    def one(r):
        return r, orchestrate.run_repo(r, args.agent, args.frm, args.to)

    if args.jobs > 1 and len(repos) > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as ex:
            results = list(ex.map(one, repos))
    else:
        results = [one(r) for r in repos]

    ok = sum(1 for _, v in results if v)
    print(f"\n=== {ok}/{len(results)} repos completed ===")
    for r, v in results:
        print(f"  {'OK ' if v else 'FAIL'} {r}")
    sys.exit(0 if ok == len(results) else 1)


if __name__ == "__main__":
    main()
