# code-bench — automated exam generator for the codegen benchmark (5 scenarios × 100 repos)

Reverse-engineers each repo into a black-box exam: a candidate-facing **spec** (contract +
modules + user stories + NFRs) and a hidden **grader** (black-box tests whose assertions are
**frozen from the original** = differential oracle). Scope: non-library scenarios
(`cli`, `service`, `pipeline`), cross-language candidates, process/network boundary.

**No repo logic is hardcoded.** Per-repo facts live in the dataset **manifest**; all per-repo
creativity (comprehension / contract / modules / stories / test inputs) is produced by the
**out-题 agent** (headless Claude) at run time. The framework is the deterministic harness +
orchestration around it.

## Run the dataset
```powershell
# 1) describe your 100 repos in a manifest (see dataset/manifest.schema.json + example)
# 2) run the whole dataset (agent drives the model stages, Docker is the substrate)
python run_dataset.py --manifest dataset/manifest.json --agent claude --jobs 8
#    one repo / a subset / a stage range:
python orchestrate.py --repo <id> --manifest dataset/manifest.json --agent claude
python run_dataset.py --manifest dataset/manifest.json --only id1,id2 --from 0 --to 5
```
Output: `out/<id>/` per repo (00_baseline … 07_verify, 05_tests/*, STATUS.json) and
`out/dataset-report.json` (per-repo stage reached / gate failures / per-module counts /
needs_review / high-water / mutation kill-rate).

## The manifest (the only thing you fill in)
`dataset/manifest.json` — one entry per repo:
```jsonc
{ "id", "scenario" (your 5 labels), "scenario_type": "cli|service|pipeline",
  "language": "go|python|rust|node|...", "source": {git|path},
  "runtime": { "mode":"docker", "dockerfile?", "cover": {"mode":"go|lcov|coveragepy|none"} },
  "service?": {port,health,env,fixtures}, "pipeline?": {in,out,cmd,compare}, "launch?":[...] }
```
Omitted fields fall back to the **language preset** (`engine/config.py`). Build/run commands a
preset can't infer can be proposed by the agent in Stage 0/1.

## Pipeline (Stage 0–7)
| stage | what | impl |
|---|---|---|
| 0 ingest | clone, build ref-image (Docker) / `-cover` binary (local), baseline test, offline smoke | `stages/stage0_ingest.py` |
| 1–4 | repo model · contract · modules+stories · NFR | agent (`prompts/stage1-4.md`) |
| 5 | **differential oracle + fill_quota (≥20/module)** | `stages/stage5_loop.py` (+ `cli_gen.py` offline stub) |
| 6 | adversarial break-the-exam | agent (`prompts/stage6.md`) |
| 7 | high-water (100% on original) + mutation kill-rate | `stages/stage7_verify.py` |

Schema + business gates (`engine/gates.py`); `STATUS.json` resume; stages 6/7 human-review.

## Engine (scenario/runtime/language-agnostic)
`runner` (Local/Docker) · `harness` (picks runner+backend per repo) · `replay` (cli /
service-HTTP / pipeline-files) · `classify` (exact/normalized/invariant/ignored, incl. http
fields) · `coverage` (go / lcov / coveragepy / none) · `grade` (mutation + candidate scoring) ·
`record_replay` (mock upstream for URL inputs) · `config` (manifest→config) · `cli_gen`
(offline equivalence-class stub).

## Benchmark a candidate (B + C — the agent under evaluation)
A (above) generates the exam. **B** drives a candidate agent (the system being evaluated)
to build a project from the candidate-facing spec; **C** grades it.
```powershell
python run_candidate.py --repo <id> --candidate-engine codex --candidate-id cand1
```
Flow: copy the spec (01–04 artifacts) into `candidates/<id>/<cid>/SPEC/` → candidate agent
(`prompts/candidate.md`, any language) writes a project + Dockerfile → `docker build` →
`grade.grade_suite` runs the frozen `05_tests` against the cand-image → `grade.score`
(per-module pass-rate + functional) → `candidates/<id>/<cid>/report.json`. The candidate
never sees the hidden tests/golden.

## What's verified vs needs-your-env
- **Verified here**: all 18 modules import + wire; manifest→config for service/cli/pipeline ×
  go/python/rust; and the full Stage 0–7 deterministic core (oracle / coverage / ≥20-quota /
  mutation 75% kill-rate) proven earlier on the cli/go path.
- **Needs your runtime (not run here — no Docker daemon / no `claude` / no dataset)**:
  `DockerRunner` + `ServiceBackend` + `PipelineBackend` end-to-end; `--agent claude` model
  stages; py/rust/node coverage collection wiring (Dockerfile entrypoints).

## Production checklist
1. Fill `dataset/manifest.json` (100 repos). 2. Pin the `docker/ref.Dockerfile.*` base digests.
3. Ensure Docker + `claude` available on the run host. 4. `python run_dataset.py --manifest …
--agent claude --jobs N`. 5. Triage `out/dataset-report.json` (Stage-0 build failures,
needs_review modules, low kill-rates) → human gate at Stage 6/7.

## Offline dev (`--agent stub`)
For a no-Claude/no-Docker smoke of the harness, `--agent stub` uses pre-authored artifacts +
`cli_gen` drafts (cli/local only). Used to validate the deterministic core.
