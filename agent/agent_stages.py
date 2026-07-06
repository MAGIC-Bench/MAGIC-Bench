"""Per-stage agent providers: stub (no live agent) vs claude (headless).

Model stages (1-4, 6): produce one artifact each.
  stub   - reuse a pre-authored artifact (must already exist) or write a trivial
           placeholder (stage 6); fails loudly if a real one is missing.
  claude - load prompts/stageN.md, inject prior artifacts, run the agent, validate.

Stage 5 draft provider: callable(modules, quota, hints) -> (drafts, needs_review).
  stub   - engine/cli_gen equivalence-class corpus.
  claude - agent writes a drafts file per round (uses uncovered-block hints).
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
sys.path.insert(0, str(ROOT / "agent"))
import cli_gen
import client
import nfr_security

ARTIFACTS = {1: ["01_repo-model.json"], 2: ["02_cli-contract.json"],
             3: ["03_modules.json", "03_user-stories.json"],
             4: ["04_nfr-labels.json"], 6: ["06_adversarial.json"]}

# Stage 2's contract file is scenario-specific, and the agent often names it freely
# (observed: a service wrote `02_openapi-contract.json`). So each scenario has ONE
# canonical name + the aliases the agent might use instead; we rename the first alias
# found to the canonical name so the gate AND candidate packaging always find it.
CONTRACT = {  # scenario_type -> (canonical, [aliases])
    "cli":      ("02_cli-contract.json",     []),
    "service":  ("02_contract.openapi.json", ["02_openapi-contract.json", "02_contract.openapi.yaml",
                                              "02_openapi.json", "02_service-contract.json"]),
    "pipeline": ("02_contract.io.json",      ["02_io-contract.json", "02_cli-contract.json"]),
}


def _normalize_contract(repo_out, scenario_type):
    """Rename the first known alias to the canonical contract name. Returns canonical."""
    canonical, aliases = CONTRACT.get(scenario_type, CONTRACT["cli"])
    dst = repo_out / canonical
    if not dst.exists():
        for a in aliases:
            src = repo_out / a
            if src.exists():
                src.rename(dst)
                break
    return canonical

PROMPTS = {1: "stage1_comprehension.md", 2: "stage2_contract.md",
           3: "stage3_modules.md", 4: "stage4_nfr.md", 6: "stage6_adversarial.md"}


def _prompt(stage, repo_dir, repo_out):
    tmpl = (ROOT / "prompts" / PROMPTS[stage]).read_text(encoding="utf-8")
    return tmpl.replace("{repo_dir}", str(repo_dir)).replace("{out_dir}", str(repo_out))


def _is_quota_error(res):
    """True if the agent's output signals a hard usage/rate limit (retrying immediately won't help)."""
    blob = ((res or {}).get("raw", "") + " " + (res or {}).get("stderr", "")).lower()
    return any(s in blob for s in ("usage limit", "rate_limit", "rate limit",
                                   "insufficient balance", "quota exceeded"))


def model_stage(stage, repo_dir, repo_out, config, mode):
    repo_out = pathlib.Path(repo_out)
    scen = config.get("scenario_type", "cli")
    arts = ARTIFACTS[stage]
    if stage == 2:                                    # contract file is scenario-specific
        arts = [CONTRACT.get(scen, CONTRACT["cli"])[0]]
    if mode == "stub":
        missing = [a for a in arts if not (repo_out / a).exists()]
        if stage == 6 and missing:
            (repo_out / "06_adversarial.json").write_text(
                json.dumps({"open_critical": 0, "notes": "stub: no adversarial agent in pilot"},
                           indent=2), encoding="utf-8")
            missing = []
        if missing:
            raise RuntimeError(f"stub mode: stage{stage} artifact(s) missing {missing}; "
                               f"author them under {repo_out} or run --agent claude")
        return True
    # live agent (mode is the engine: "claude" | "codex"). RETRY on no-write: a single agent flake
    # (brief rate-limit / occasional skipped write) must NOT waste the whole repo. Re-invoke up to N times.
    attempts = config.get("model_stage_attempts", 3)
    missing = list(arts)
    for _i in range(attempts):
        res = client.run_headless(_prompt(stage, repo_dir, repo_out), cwd=str(repo_out),
                                  allowed_tools=["Read", "Grep", "Glob", "Write", "Bash"],
                                  engine=mode, add_dirs=[str(repo_dir)])
        if stage == 2:                                # the agent may have named the contract freely
            _normalize_contract(repo_out, scen)
        missing = [a for a in arts if not (repo_out / a).exists()]
        if not missing:
            return True
        if _is_quota_error(res):                      # hard usage-limit: retrying won't help -> fail clearly
            raise RuntimeError(f"{mode} stage{stage}: 额度/限流 (usage limit) — 没写 {missing}；等额度重置或充值")
    raise RuntimeError(f"{mode} stage{stage} did not write {missing} after {attempts} attempt(s)")


def adversarial_review(repo_dir, repo_out, config, mode, focus_ids=None):
    """Stage 6 review (writes 06_adversarial.json). focus_ids=None -> FULL review of all cases; a list
    -> SCOPED re-review of ONLY those just-repaired cases (cheaper -- the rest were already cleared by
    the prior full review). Stub mode writes a trivial pass."""
    repo_out = pathlib.Path(repo_out)
    if mode == "stub":
        p = repo_out / "06_adversarial.json"
        if not p.exists():
            p.write_text(json.dumps({"open_critical": 0, "findings": [], "notes": "stub"}, indent=2),
                         encoding="utf-8")
        return
    focus = ""
    if focus_ids:
        focus = ("\nSCOPED RE-REVIEW: the cases below were just repaired. Re-examine ONLY these and judge "
                 "whether each STILL has a critical issue (a deleted/missing case = resolved). "
                 "`open_critical` = the count among THESE that remain critical; do NOT review other cases:\n  "
                 + ", ".join(focus_ids) + "\n")
    tmpl = (ROOT / "prompts" / "stage6_adversarial.md").read_text(encoding="utf-8")
    prompt = (tmpl.replace("{repo_dir}", str(repo_dir)).replace("{out_dir}", str(repo_out))
              .replace("{focus}", focus))
    out = repo_out / "06_adversarial.json"
    attempts = config.get("model_stage_attempts", 3)   # RETRY on no-write (same as model_stage)
    for _i in range(attempts):
        res = client.run_headless(prompt, cwd=str(repo_out),
                                  allowed_tools=["Read", "Grep", "Glob", "Write", "Bash"],
                                  engine=mode, add_dirs=[str(repo_dir)])
        if out.exists():                               # written now, or pre-existed for a scoped re-review
            return
        if _is_quota_error(res):
            raise RuntimeError(f"{mode} stage6: 额度/限流 (usage limit) — 没写 06_adversarial.json；等额度重置或充值")
    raise RuntimeError(f"{mode} stage6 did not write 06_adversarial.json after {attempts} attempt(s)")


def repair_stage6(repo_dir, repo_out, config, mode, findings):
    """Feed stage6's CRITICAL findings back to the agent to repair ONLY the flagged 05_tests cases
    (prompts/stage6_repair.md). Mirrors the stage0 build-repair: review -> repair -> re-review."""
    repo_out = pathlib.Path(repo_out)
    crit = [f for f in (findings or []) if f.get("severity") == "critical"]
    if not crit:
        return
    tmpl = (ROOT / "prompts" / "stage6_repair.md").read_text(encoding="utf-8")
    prompt = (tmpl.replace("{out_dir}", str(repo_out))
              .replace("{findings}", json.dumps(crit, ensure_ascii=False, indent=1)))
    client.run_headless(prompt, cwd=str(repo_out),
                        allowed_tools=["Read", "Grep", "Glob", "Write", "Bash"],
                        engine=mode, add_dirs=[str(repo_dir)])


def draft_provider(repo_dir, repo_out, config, mode):
    repo_out = pathlib.Path(repo_out)
    if mode == "stub":
        def provider(modules, quota, hints):
            return cli_gen.generate(modules, quota)
        return provider

    # req 2.7: security metrics the ORIGINAL already implements -> the agent must ALSO emit tagged
    # security drafts for them. Computed once from stage4's output (empty list -> no security section).
    sec = nfr_security.pick_security_metrics(repo_out)
    sec_str = ", ".join(f"{s['metric_id']} ({s['name']}, kind={s['kind']})" for s in sec) or "(none)"

    def provider(modules, quota, hints):
        tmpl = (ROOT / "prompts" / "stage5_gen.md").read_text(encoding="utf-8")
        prompt = (tmpl.replace("{repo_dir}", str(repo_dir)).replace("{out_dir}", str(repo_out))
                  .replace("{modules}", ",".join(modules)).replace("{quota}", str(quota))
                  .replace("{hints}", json.dumps(hints[:40])).replace("{sec_metrics}", sec_str))
        client.run_headless(prompt, cwd=str(repo_out),
                            allowed_tools=["Read", "Grep", "Glob", "Write", "Bash"],  # Grep/Glob: mine repo tests
                            engine=mode, add_dirs=[str(repo_dir)])
        drafts = json.loads((repo_out / "_drafts_round.json").read_text(encoding="utf-8"))
        return drafts, []
    return provider
