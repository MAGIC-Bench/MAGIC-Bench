You are the exam-generation agent. STAGE 4 — label the NFR metrics for THIS repo (per-metric applicability).

INPUT:
- The metrics table `{out_dir}/nfr-metrics.json` — every metric has id / dimension / kind (static|runtime) /
  scoring (binary|ratio100) / desc. Read it.
- The ORIGINAL repo at `{repo_dir}` and prior artifacts `{out_dir}/01_repo-model.json`, `02_*`, `03_*`.

For EACH metric in nfr-metrics.json, judge whether it is RELEVANT to TEST for a re-implementation of THIS
repo, from the repo's domain + behavior. You are NOT scoring the candidate here — only deciding what to
measure later. Output one label per metric.

`applies=true` when the metric is meaningful for this repo. Guidance:
- **SEC1 未授权读 / SEC4 未授权写**: applies ONLY if the repo has a protected resource or permission/path
  boundary (auth, ACL, a path it must not escape, a target it must not touch). A stateless CLI with no
  protected target → applies=false.
- **SEC5 SQL注入**: applies ONLY if the repo builds/executes SQL (or a similar injectable query language).
- **SEC3 加密存储**: applies ONLY if the repo persists sensitive fields (DB/file/credential store).
- **SEC6 审计日志**: applies ONLY if the repo's domain requires audit logging.
- **CMP2 接口契约**: applies if there is a machine-readable contract (CLI flags/exit codes or HTTP) to validate.
- **RLY3 DB断连**: applies ONLY if the repo needs a database connection. **RLY** generally applies to any
  long-running/stateful tool; for a one-shot CLI keep only the ones that make sense (e.g. RLY5 并发, RLY1 长时).
- **MTN / PTB (静态)**: generally applies to ANY code repo (they grade the candidate's own source).
- **PERF1 无崩溃 / PERF4 限时正确通过**: ALWAYS applies (functional correctness + no-crash baseline).
- **PTB6 平台绑定**: only when the repo plausibly targets multiple platforms.

Keep each metric's `kind` and `scoring` from nfr-metrics.json. For each **runtime** metric that applies, add
a short `probe_hint` — concretely how to exercise a candidate to measure it (what input/load/fault to apply,
what observable decides pass/fail). Static metrics need no probe (codex will scan the candidate's source at
grading per the metric's desc).

Write `{out_dir}/04_nfr-labels.json`:
```
{ "labels": [ { "metric_id", "dimension", "kind", "scoring",
                "applies": true|false, "justification": "<one line>",
                "probe_hint": "<only for applies=true runtime metrics>" }, ... ],
  "applicable": [ "<metric_id of EVERY applies=true metric>" ] }
```
Every metric in nfr-metrics.json must appear exactly once in `labels`. Output only the path you wrote.
