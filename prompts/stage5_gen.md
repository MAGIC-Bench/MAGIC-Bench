You are the exam-generation agent. STAGE 5 — generate test INPUTS (no expected values).

Under-quota modules this round: {modules}   (quota per module: {quota})
Uncovered-block hints from the original (cover these): {hints}

Read {out_dir}/02_cli-contract.json and {out_dir}/03_user-stories.json.

ALSO mine the ORIGINAL repo's OWN tests for input ideas: the source is at {repo_dir}. Look in its test
dirs (tests/, test/, testdata/, spec/, examples/, *_test.*, *.test.*) for process-boundary scenarios —
cli invocations, request sequences, or input datasets — and translate the INPUTS into drafts below. Take
ONLY the inputs (argv / stdin / files / steps); NEVER copy the repo's expected/asserted values — golden
is frozen by running the original. This harvests real-world edge cases the contract alone wouldn't suggest.

Produce input drafts (a JSON array). Each draft exercises a NEW equivalence class /
boundary / error path for an under-quota module, OR covers a hinted block. Schema:
  { "id": "...", "modules": ["M?"], "kind": "intent|incident",
    "security_metric": "<metric_id>"  (OPTIONAL, only for the security cases below),
    "input": { "argv": [...], "stdin": "<utf8>"  (OR)  "files": {"name": {"text": "..."}} },
    "assert_spec": [ {"field": "...", "class": "...", "rule": "...", "note": "..."} ] }

SECURITY TEST CASES (req 2.7) — the ORIGINAL already satisfies these security metrics: {sec_metrics}
  For EACH metric listed above (skip this whole block if the list is empty / says "(none)"), ALSO emit
  at least 3 drafts that probe that security property as BLACK-BOX behavior, each carrying
  `"security_metric": "<that metric_id>"` AND a real `modules` tag (the module whose input you attack):
    - unauthorized_access / unauthorized_modify — feed an input that attempts to read/modify a resource
      the actor is NOT permitted to (e.g. a path OUTSIDE the working dir, a protected target, a forged
      credential) and assert the program SAFELY REFUSES with a GRADEABLE signal: a non-crash error exit
      (`invariant:eq_int:<refuse-code>`) AND, whenever the original prints one, a stable refusal marker on
      stderr/stdout (`invariant:regex:<marker>`). NEVER assert exit 0 for a blocked operation. If the
      operation must leave a protected target UNCHANGED, you MAY positively pin that target's unchanged
      content with `file:<relpath>` exact (out_files only captures the run workdir).
    - malicious_input (injection / tamper / path-traversal / parse-bomb) — feed adversarial input
      (`../../etc/passwd`, embedded NUL, a SQL/shell metacharacter payload, a deeply-nested / oversized
      doc) and assert the program HANDLES it safely with a GRADEABLE signal: a sane non-crash exit
      (`invariant:eq_int:<n>`, or a small set via `invariant:regex`) AND, when the original emits a stable
      safe-output marker, pin it on stderr/stdout with `invariant:regex:<marker>` (this also satisfies the
      content-coverage requirement below). You CANNOT assert the ABSENCE of a panic/stack-trace via regex
      (regex only matches presence) — so do NOT try; instead pin a POSITIVE marker of the documented safe
      behavior. Golden is frozen by running the original, so only assert what the ORIGINAL actually does
      safely; if the original itself crashes on the payload, DROP that draft (never freeze a crash as golden).
  NOTE: file side effects OUTSIDE the run workdir are blocked by the sandbox and are NOT expressible as
  assertions — do not write a `file:<path>` field to express the ABSENCE of a write. The gradeable signal
  for a security case is exit + (where available) a stderr/stdout marker, plus optionally an unchanged
  protected file via `file:<relpath>` exact.
  Security drafts go in the SAME JSON array as the functional drafts. They are observable, double-run
  frozen, and graded exactly like other cases — the `security_metric` tag is what marks them as the
  evidence for that NFR metric.

field = "exit" | "stdout" | "stderr" | "file:<relpath>"
class + rule — use ONLY these; pick the MOST LENIENT class that still pins the behavior:
  - "exact"       -> NO "rule". Byte/value identical to the original (exit codes; tightly
                    specified output like sorted monochrome gron).
  - "normalized"  -> "rule" is EXACTLY one of:
                    "crlf_lf" | "strip" | "rstrip_eol" | "lines_sorted" | "json_canonical" | "regex_extract:<regex>"
  - "invariant"   -> "rule" is EXACTLY one of:
                    "nonempty" | "empty" | "valid_json" | "regex:<regex>" | "eq_int:<n>"
  - "ignored"     -> NO "rule" (present but unchecked, e.g. error-message wording).

HARD RULES:
- SELF-CONTAINED: the harness RESETS external state (DB/cache) before EVERY test, so each test must
  establish ALL its own preconditions within its own steps — e.g. to test "login", first "register"
  in the SAME test sequence. NEVER assume state left by another test (= dangling state).
- STATEFUL CLI TOOLS (a tool with a PERSISTENT registry / config / cache that survives across separate
  invocations — e.g. a tool where you must FIRST `add`/`register` a named handle in one invocation and
  THEN use `@handle` in a later one): a single-invocation CLI test CANNOT carry state between invocations,
  and the harness wipes that state before each test, so any test referencing a handle/source/profile that
  a PRIOR command would have created WILL fail to reproduce at verification and be DROPPED. Therefore
  prefer STATELESS, one-shot invocations whose entire input is provided IN the test: pass data via stdin
  or an inline `files` payload, do deterministic one-shot conversions/queries/diffs over THAT provided
  data, and use canonical output (`json_canonical`, `lines_sorted`) for order/format-unstable output. Do
  NOT generate tests that depend on a registry entry, saved config, or cached DB established by a separate
  earlier invocation — they are not self-contained and will be dropped.
- DO NOT write expected values — they are frozen by running the original.
- "rule" MUST be one of the keywords above — NEVER a sentence. Put any human reasoning in
  the optional "note" field, never in "rule".
- CROSS-IMPLEMENTATION FAIRNESS — use exact/normalized ONLY for values the contract fixes.
  Mark `ignored` (or `invariant:regex` for a loose check) for anything a *different correct*
  implementation (especially a DIFFERENT LANGUAGE) would word or format differently:
    * parser / runtime error MESSAGES — e.g. a YAML parser's exact "syntax error: expected ','
      or ']', but got '<stream end>'" wording is library-specific; Go/Rust/Node libs phrase it
      differently, and the contract cannot pin it. NEVER exact/normalized on such text.
    * the program's OWN NAME and any help / usage / version BANNER — the candidate is de-identified and
      MUST be referred to as `app`; the original's real name is scrubbed from the candidate's contract.
      NEVER put the original program/repo NAME into ANY assertion — not in an `exact`/`normalized`
      VALUE, and NOT inside an `invariant:regex`/`normalized:regex_extract` RULE either (e.g. do NOT
      write `regex:^jd version` or `regex:Refurb:` — those name-bearing rules fail a correct candidate
      that prints `app version ...`). For `--help`/`-h`/usage/version output assert only the stable,
      NAME-FREE structure via `invariant:regex` (e.g. `regex:version\s+[0-9]`), otherwise `ignored`.
    * INTERNAL IMPLEMENTATION SYMBOLS — class / type / AST-node names, struct fields, package/module
      paths (e.g. `MypyFile`, `ExpressionStmt`, `github.com/owner/...`) are white-box detail of ONE
      implementation; a correct reimpl emits different ones. NEVER exact/normalized on them.
    * language/version strings, stack traces, ANSI color bytes, map/iteration order, timestamps.
- AVOID INHERENTLY WHITE-BOX MODES — do not write a test whose WHOLE asserted output is implementation
  internal: debug / introspection dumps (AST-node reprs like `StrExpr(...)`, `--debug` traces), internal
  type spellings (`list[Error]`), or a tool's complete internal check / rule INVENTORY (a `--verbose`
  dump of every built-in rule). No two implementations produce these identically, so they cannot be
  graded black-box — SKIP these modes entirely rather than trying to assert them leniently.
- AVOID INTERNAL-API / PLUGIN FEATURES — do not write tests for extension / plugin mechanisms that
  require importing or subclassing the tool's INTERNAL API (e.g. a custom check whose fixture does
  `from <tool>.error import Error` and subclasses an internal class). No reimplementation can provide
  the original's internal modules, so the feature is untestable black-box — SKIP it.
- HOST-ENVIRONMENT outputs are NOT contract behavior — mark `ignored`/`invariant`. If a value comes
  from the host (current username, hostname, locale, timezone, free disk, system volume, surrounding
  wifi/network, random / PID / temp paths) a correct reimpl on a different host yields a different
  value, so a frozen golden for it is a poison.
- NO TIMEOUT / NETWORK ARTIFACTS AS GOLDEN: never write an input whose asserted behavior depends on a
  network fetch or external service, or that could TIME OUT (exit 124 is a timeout artifact, not a
  contract behavior). Only assert a network/offline result if the test EXPLICITLY exercises that
  documented behavior.
- CONTENT COVERAGE (not just exit): a test that pins only `exit` is weak — a garbage-stdout impl with
  the right exit code would pass. Each test SHOULD also pin at least one CONTENT field
  (stdout / stderr / file:<path>) with `exact` or `normalized` whenever the contract fixes that
  output. Across the round, the MAJORITY of tests must pin a content field exact/normalized
  (a gate enforces ≥50%); `exit` alone does NOT satisfy this.
- ARGV EXCLUDES THE PROGRAM NAME — `argv` is the arguments AFTER the program. The harness invokes the
  program (its entrypoint) and APPENDS your `argv`. NEVER put the program / binary / tool name as an
  argv element: write `argv: ["lint","f.py"]`, NOT `["mytool","lint","f.py"]`. A program name in argv
  becomes a bogus first positional argument (and such drafts are dropped before they reach golden).
- DON'T FREEZE A CONTRACT-VIOLATING ORIGINAL — read 02's `exit_codes` + documented behavior. For an
  input the contract says MUST error (e.g. malformed input → exit 2), ASSERT that contract value as an
  `invariant` — `{"field":"exit","class":"invariant","rule":"eq_int:2"}` — NOT `exact`. The engine
  freezes golden by running the original and CHECKS your invariant against it: if the original is buggy
  and disobeys its own contract (returns success / a different code), the invariant fails and the engine
  DROPS the case automatically — so the original's bug never becomes golden. Asserting the documented
  contract value as an invariant is how "keep only inputs where the original obeys its contract" actually
  gets enforced; never pin an error path with `exact` on a success/`exit 0` you did not expect.
- MIX INTENT + INCIDENT — do not make every test an error path. Each module needs at least one
  `kind:"intent"` happy-path test (normal, successful use) alongside its `incident` (boundary/error) tests.
- A draft may carry several module tags if one invocation exercises several modules.

Write the JSON array to {out_dir}/_drafts_round.json. Output only that path.
