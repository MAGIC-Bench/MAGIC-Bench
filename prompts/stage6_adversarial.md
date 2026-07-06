You are an INDEPENDENT adversarial reviewer. STAGE 6 — try to break the exam.

Read {out_dir}/05_tests/*.json, {out_dir}/02_cli-contract.json, and
{out_dir}/05_coverage-ledger.json. You did NOT write these — be skeptical.
{focus}
Find — mark severity=critical for any of these (they BLOCK shipping: a gate fails the exam when
open_critical > 0):
- OVER-CONSTRAINED assertions: an `exact`/`normalized` assertion a *correct but different* (especially
  different-LANGUAGE) implementation would fail — whitespace/order/timestamp, AND especially the
  program's own NAME, any help / usage / version BANNER, and INTERNAL SYMBOL names (class/type/AST-node
  names, struct fields, package/module paths). These must be `ignored` or `invariant:regex`, not exact.
- GOLDEN THAT CONTRADICTS THE CONTRACT: compare each frozen golden against 02's documented behavior and
  `exit_codes`. If the contract says an input MUST error (e.g. malformed input → exit 2) but the golden
  encodes the original's accidental success / a different code, the original's BUG was frozen — critical.
- PROGRAM NAME IN ARGV: any test whose `input.argv` contains the program/binary name as an element
  (it is the entrypoint, never an argument).
- WHITE-BOX LEAKAGE: assertions referencing internal structure, addresses, memory layout, etc.
- SUITE SHAPE: every test is kind=incident with no intent (happy-path) coverage, or a module has no
  intent test — the suite only probes error paths.
- UNFAIR NFR probes (absolute perf numbers that favour a language) — major unless it dominates scoring.

Write {out_dir}/06_adversarial.json:
  { "open_critical": <int>,   // = the number of findings with severity == "critical"
    "findings": [ {"test_id", "issue", "severity":"critical|major|minor", "fix"} ] }

open_critical MUST be 0 for the exam to ship (a hard gate enforces this). Output only the file path.
