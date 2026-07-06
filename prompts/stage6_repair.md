You are the exam-repair agent. The INDEPENDENT adversarial reviewer (STAGE 6) found CRITICAL,
shipping-blocking problems in the frozen test cases. Fix EXACTLY those, minimally — do not touch
anything not named below.

CRITICAL findings (each has the offending test_id(s), the issue, and a recommended fix):
{findings}

The test cases are JSON files in {out_dir}/05_tests/. A finding's `test_id` is the case id, i.e.
{out_dir}/05_tests/<test_id>.json. A test_id may name several cases (comma-separated) or a pattern
(`suite:...`, `ALL_05_tests`) — apply the fix to EVERY case it refers to (Grep/Glob 05_tests to find
them). Also read {out_dir}/02_*-contract.json for the documented behavior.

For each finding, edit ONLY the named case file(s), applying its `fix`:
- OVER-CONSTRAINED assertion — `exact`/`normalized` on the program NAME, a help/usage/version BANNER,
  or an INTERNAL SYMBOL (AST-node / class / type / package name): change that assertion to
  `{"field": ..., "class": "invariant", "rule": "regex:<core>"}` where `<core>` pins ONLY the
  cross-implementation-stable structural part (the error code, field layout, the stable phrase) and NOT
  the name/banner/symbol. The regex MUST still match this case's `observed` value, so the original
  still passes. Use `"class": "ignored"` ONLY when no fair structural check exists. Keep `exit` and any
  already-fair assertion as-is.
- GOLDEN CONTRADICTS THE CONTRACT (the original's BUG was frozen — e.g. the contract says malformed
  input → exit 2 but golden froze exit 0): DELETE that case file. The original's bug must not be the key.
- PROGRAM NAME IN ARGV (the program/binary name appears as an `input.argv` element): DELETE that case
  file — the program is the entrypoint, never an argument.
- WHITE-BOX LEAKAGE: treat like over-constrained — regex the public part, else `ignored`.
- INHERENTLY WHITE-BOX FEATURE (a case that can ONLY pass by importing or subclassing the ORIGINAL's
  INTERNAL API — plugin / extension / custom-check loaders whose fixtures do e.g. `from <tool>.error
  import Error` and subclass an internal class): DELETE the case file. No reimplementation can provide
  the original's internal modules, so the feature is untestable black-box — do NOT try to regex it.
- NO STABLE CORE: if a flagged assertion has NO cross-implementation-stable structural part to regex
  (it is entirely implementation-internal), DELETE the case rather than forcing a weak/ignored assertion.

HARD RULES:
- VALID ASSERTION GRAMMAR ONLY — every assertion you write MUST use these EXACT forms; inventing a rule
  crashes the grader. `class` ∈ {exact, normalized, invariant, ignored}.
    - normalized `rule` ∈ {crlf_lf, strip, rstrip_eol, lines_sorted, json_canonical, regex_extract:<re>}
    - invariant  `rule` ∈ {nonempty, empty, valid_json, regex:<re>, eq_int:<n>}
  NEVER invent a domain rule (e.g. `rfc6902_transforms:...`). To check structured / JSON-patch output use
  `invariant:valid_json`, `normalized:json_canonical`, or `invariant:regex:<re>` — nothing else.
- Touch ONLY cases named in the findings. Do NOT edit, delete, or weaken any other case.
- Do NOT blanket-`ignored` everything: an anti-gaming gate requires the suite to keep ≥50% of cases
  pinning a CONTENT field (stdout/stderr/file) with a real value check (exact / normalized / invariant
  `regex:`/`eq_int:`/`valid_json`). ALWAYS prefer `invariant:regex` over `ignored`.
- Preserve each edited file's other fields (id, modules, input, observed, kind) unchanged; only adjust
  the offending entries in `assertions` (or delete the whole case when instructed above). Keep JSON valid.

When done, output the list of case files you edited or deleted.
