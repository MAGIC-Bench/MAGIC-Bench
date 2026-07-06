"""Go coverage adapter for the differential-oracle loop.

A `go build -cover` binary writes coverage counters to $GOCOVERDIR on exit (yes,
even when the program calls os.Exit). We collect one cover dir per black-box run,
then merge them with `go tool covdata`:

  percent()      -> overall statement coverage across the merged runs
  ledger()       -> per-block covered/uncovered list, parsed from `covdata textfmt`

The uncovered blocks feed the loop as behaviour-discovery hints; the reachability
pass (a model step in the full pipeline) then marks each block target|excluded.
"""
from __future__ import annotations

import subprocess


def _i(cover_dirs):
    return ",".join(d for d in cover_dirs if d)


def percent(cover_dirs, go="go") -> str:
    p = subprocess.run([go, "tool", "covdata", "percent", f"-i={_i(cover_dirs)}"],
                       capture_output=True, text=True)
    return (p.stdout or p.stderr).strip()


def pct_value(cover_dirs, go="go") -> float:
    """Parse the float percentage out of `covdata percent`."""
    import re
    txt = percent(cover_dirs, go)
    m = re.search(r"coverage:\s*([\d.]+)%", txt)
    return float(m.group(1)) if m else 0.0


def textfmt(cover_dirs, out_path, go="go") -> str:
    subprocess.run([go, "tool", "covdata", "textfmt",
                    f"-i={_i(cover_dirs)}", f"-o={out_path}"], check=True,
                   capture_output=True, text=True)
    return out_path


def parse_profile(path):
    """Parse a Go coverage profile into {covered:[loc], uncovered:[loc]}.

    Each non-header line is:  file:startLine.col,endLine.col numStmt count
    """
    covered, uncovered = [], []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("mode:"):
                continue
            loc, _stmts, count = line.rsplit(" ", 2)
            (covered if int(count) > 0 else uncovered).append(loc)
    return {"covered": covered, "uncovered": uncovered}


def ledger(cover_dirs, out_path, go="go"):
    """Merge runs -> block-level ledger with a coverage percentage."""
    textfmt(cover_dirs, out_path, go)
    prof = parse_profile(out_path)
    total = len(prof["covered"]) + len(prof["uncovered"])
    prof["block_coverage"] = (len(prof["covered"]) / total) if total else 0.0
    prof["pct_statements"] = pct_value(cover_dirs, go)
    return prof
