"""Stage 8 - package the exam into two bundles:

  07_exam/grader/    做题侧 (hidden from the candidate agent)
    - pytest black-box suite (engine/pytest_emit) + cases/  (+ _grader_meta.json, deps.py for service)
    - nfr_applicable.json       (the NFR metrics Stage 4 labeled applies=true; the scorer grades these)
    - rewritable_languages.json (the languages the repo could be reimplemented in)

  07_exam/candidate/ 卷面 (the canonical exam package — the ONLY thing a candidate ever sees)
    - 项目描述.md              (de-identified business brief; req 2.1)
    - 用户API使用手册.md        (human-readable API manual rendered from the scrubbed contract; req 2.2)
    - 功能模块文档.md           (feature list, NO module IDs; req 9)
    - 用户行为示例文档.md        (user stories, NO module tags; req 9)
    - 非功能需求.md             (the measurable NFRs to satisfy)
    - 02_*-contract.json        (machine contract, binary/repo name SCRUBBED; req 2.1 anti-cheat)
    - generation_language.txt   (the required language = rewritable[0]; req 7)
    - prompt.md                 (the task prompt)
"""
from __future__ import annotations

import copy
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "engine"))
import deident
import pytest_emit

GENERIC_BIN = deident.GENERIC   # neutral placeholder for the original binary/tool name in candidate files


def _load(p, default):
    p = pathlib.Path(p)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _modules_md(modules):
    # candidate-facing FEATURE list (issue 9): NO internal module IDs (M1/M2...). The candidate is
    # free to organize its own architecture; the grader still tags cases by module internally.
    out = ["# 功能清单\n", "> 实现以下每一项功能。代码结构由你自由组织。\n"]
    for i, m in enumerate(modules.get("modules", []), 1):
        out.append(f"## {i}. {m.get('name', '')}")
        if m.get("user_value"):
            out.append(f"- 用户价值:{m['user_value']}")
        for k in ("ops", "flags", "inputs", "exit_codes"):
            if m.get(k):
                out.append(f"- {k}: {', '.join(map(str, m[k]))}")
        out.append("")
    return "\n".join(out)


def _stories_md(stories):
    out = ["# 用户行为示例文档\n",
           "> 格式:参与者 / 前置状态 / 触发动作 / 预期结果 + 可执行调用代码。\n"]
    for s in stories.get("stories", []):
        out.append(f"## {s['id']}")          # issue 9: no module tags -> module organization stays internal
        pr = s.get("prose", {})
        for k, lbl in [("actor", "参与者"), ("precondition", "前置状态"),
                       ("trigger", "触发动作"), ("expected", "预期结果")]:
            if pr.get(k):
                out.append(f"- {lbl}:{pr[k]}")
        if s.get("code"):
            out.append("```\n" + "\n".join(s["code"]) + "\n```")
        out.append("")
    return "\n".join(out)


def _brief_md(brief):
    return "# 项目描述\n\n" + (str(brief).strip() or "(未提供项目描述)") + "\n"


def _scrub_contract(contract, toks):
    """Scrub every identity token out of the contract VALUES (keys kept = structure). Grading is by
    ENTRYPOINT/golden, not by contract text, so renaming the tool to `app` is safe (req 2.1 anti-cheat)."""
    def scrub(o):
        if isinstance(o, str):
            return deident.scrub_text(o, toks)
        if isinstance(o, list):
            return [scrub(x) for x in o]
        if isinstance(o, dict):
            return {k: scrub(v) for k, v in o.items()}      # scrub VALUES, keep keys (structure)
        return o

    out = scrub(copy.deepcopy(contract))
    if isinstance(out.get("binary"), str):
        out["binary"] = GENERIC_BIN
    if isinstance(out.get("info"), dict):                    # openapi: drop identifying title/description
        for k in ("title", "description"):
            out["info"].pop(k, None)
    out.pop("servers", None)
    return out


def _api_manual_md(contract, scen):
    out = ["# 用户 API 使用手册\n",
           f"> 你必须对外暴露的接口契约(已脱敏)。占位名 `{GENERIC_BIN}` 仅代表你的程序入口,实际名称由你决定。\n"]
    if not contract:
        out.append("(契约缺失。)")
        return "\n".join(out) + "\n"
    if scen == "cli":
        if contract.get("usage"):
            out.append("## 用法\n```\n" + str(contract["usage"]) + "\n```")
        flags = contract.get("flags") or []
        if flags:
            out.append("\n## 参数 / Flags\n| 长选项 | 短选项 | 类型 | 说明 |\n|---|---|---|---|")
            for f in flags:
                out.append(f"| {f.get('long','')} | {f.get('short','')} | {f.get('type','')} | {f.get('doc','')} |")
        ec = contract.get("exit_codes") or {}
        if ec:
            out.append("\n## 退出码\n| 码 | 含义 |\n|---|---|")
            for k, v in ec.items():
                out.append(f"| {k} | {v} |")
        io = contract.get("io_contract") or {}
        if io:
            out.append("\n## 输入 / 输出")
            for k in ("stdin", "stdout", "stderr", "color"):
                if io.get(k):
                    out.append(f"- **{k}**:{io[k]}")
    elif scen == "service":
        out.append("## HTTP 端点")
        for path, methods in (contract.get("paths") or {}).items():
            if isinstance(methods, dict):
                for method, spec in methods.items():
                    summ = spec.get("summary", "") if isinstance(spec, dict) else ""
                    out.append(f"- `{method.upper()} {path}` — {summ}")
    elif scen == "pipeline":
        for k in ("invocation", "command", "cmd", "input", "output", "exit_codes"):
            if contract.get(k):
                out.append(f"- **{k}**:{json.dumps(contract[k], ensure_ascii=False)}")
    return "\n".join(out) + "\n"


def _nfr_md(applicable, security=None):
    """applicable: list of {metric_id, dimension, name, desc, kind} -- the NFR metrics this repo is
    graded on (Stage-4 labeled applies=true)."""
    out = ["# 非功能需求(NFR)\n", "> 你的实现会在以下非功能指标上被评估(按维度分别计分)。\n"]
    if not applicable:
        out.append("(本项目无适用的非功能需求。)")
    by_dim = {}
    for m in applicable:
        by_dim.setdefault(m.get("dimension", "?"), []).append(m)
    for dim in sorted(by_dim):
        out.append(f"## {dim}")
        for m in by_dim[dim]:
            out.append(f"- **{m.get('metric_id')}** {m.get('name', '')}:{m.get('desc', '')}")
        out.append("")
    if security:
        out.append("## 安全性专项测试")
        out.append("> 卷面针对以下安全指标附带了行为测试用例,你的实现必须安全地处理对应的恶意/越权输入:")
        for s in security:
            out.append(f"- **{s.get('name', s['metric_id'])}**({s['metric_id']}):{s['count']} 条测试用例")
        out.append("")
    return "\n".join(out)


def _prompt_md(gen_lang, scenario_type, dependencies=None):
    deps = dependencies or []
    deps_md = ""
    if deps:
        items = "\n".join(
            f"  - **{d.get('kind','?')}**:运行时由评测起好,**通过环境变量 `{d.get('env','?')}` 注入完整连接串"
            f"(含主机/端口/账号/密码)**。你的实现必须从该环境变量读取连接,**严禁硬编码**主机/端口/账号/密码;"
            f"判卷会在每个用例前清空其数据,不要假设有持久化的预置数据。"
            for d in deps)
        deps_md = ("\n- **外部依赖(评测在运行时起好并注入,你不用自己装/起这些 DB/缓存)**:\n" + items)
    return f"""# 任务

用 **{gen_lang}** 实现一个项目,使其对外可观察行为符合本卷面所给的描述与契约。

- 场景类型:**{scenario_type}**
- 阅读全部卷面文件,实现其中每一项功能:
  - `项目描述.md` — 业务背景(它为用户解决什么问题)
  - `用户API使用手册.md` — 你必须对外暴露的接口(命令/参数/退出码/IO 或 HTTP 端点)
  - `功能模块文档.md` — 必须实现的功能清单
  - `用户行为示例文档.md` — 典型用户行为示例(无期望值)
  - `非功能需求.md` — 需满足的非功能要求
  - `02_*`(若有)— 机器可读契约,与使用手册一致
- 必须对外暴露与契约**完全一致**的接口:
  - cli → 相同的 flag / 退出码 / stdin·stdout·文件副作用
  - service → 相同的 endpoint / 状态码 / 报文;监听 `$PORT`,提供健康检查
  - pipeline → 相同的输入路径→输出路径契约{deps_md}
- 交付一个 `build.sh`(本目录根),原生构建你的实现,**不要用 Docker**(评测机无 docker):
  - 构建期可联网;用国内镜像(pip 清华 / GOPROXY=goproxy.cn / npm npmmirror / cargo USTC),**不要离线/frozen 安装**。
  - 依赖隔离进本目录(python `.venv` / rust `target` / node `node_modules`),`build.sh` 成功 exit 0。
  - 写一个 `run.json`:`{{"launch": ["<运行你工具的命令行 argv,绝对路径>"], "smoke": ["--help 之类"]}}`
    cli → `launch` 即你的 CLI(评测在其后追加参数);service → `launch` 启服务监听 `$PORT`;pipeline → 输入路径→输出路径。
- 判卷是**黑盒**:`build.sh` 构建后,评测以 `launch` 跑冻结的双跑用例,比对输出格式 / 状态码 / 退出码 / 文件副作用。
"""


def run(repo_out, config, exam_dir=None, generation_language=None, rewritable_languages=None):
    repo_out = pathlib.Path(repo_out)
    scen = config.get("scenario_type", "cli")
    exam = pathlib.Path(exam_dir or (repo_out / "07_exam"))
    grader, cand = exam / "grader", exam / "candidate"
    grader.mkdir(parents=True, exist_ok=True)
    cand.mkdir(parents=True, exist_ok=True)

    rm = _load(repo_out / "01_repo-model.json", {})
    # NFR: Stage-4 labels (which metrics apply to this repo) joined with the metrics table (name/desc/dim/kind/scoring).
    labels = _load(repo_out / "04_nfr-labels.json", {})
    metrics_idx = {str(m.get("id")): m for m in _load(repo_out / "nfr-metrics.json", {}).get("metrics", [])}
    _appset = {x for x in (labels.get("applicable") or []) if isinstance(x, str)}
    for lab in labels.get("labels", []):
        if isinstance(lab, dict) and lab.get("applies") and lab.get("metric_id"):
            _appset.add(lab["metric_id"])
    applicable = [{"metric_id": mid, "dimension": metrics_idx.get(mid, {}).get("dimension", "?"),
                   "name": metrics_idx.get(mid, {}).get("name", ""), "desc": metrics_idx.get(mid, {}).get("desc", ""),
                   "kind": metrics_idx.get(mid, {}).get("kind", ""), "scoring": metrics_idx.get(mid, {}).get("scoring", "binary")}
                  for mid in sorted(_appset)]

    # de-identification tokens (binary + repo name): scrub BOTH the hidden golden (grader/cases) AND the
    # visible candidate docs, so a correct candidate printing 'app' isn't failed by a golden still naming
    # the original, and the candidate package can't be used to re-identify the repo (req 2.1).
    contract, contract_name = None, None
    for c in ("02_cli-contract.json", "02_contract.openapi.json", "02_contract.io.json"):
        if (repo_out / c).exists():
            contract, contract_name = _load(repo_out / c, {}), c
            break
    toks = deident.identity_tokens(rm.get("repo_id"), (contract or {}).get("binary"))

    # ---- 做题侧 (hidden) ----
    runtime = {"scenario_type": scen, "service": config.get("service"),
               "pipeline": config.get("pipeline"), "dependencies": config.get("dependencies")}
    emitted = pytest_emit.emit(repo_out, grader, scen, runtime, scrub_tokens=toks)
    n_tests = emitted["n_tests"]
    # grader input for the NFR scorer (Phase C): exactly the metrics this candidate is graded on.
    (grader / "nfr_applicable.json").write_text(
        json.dumps({"applicable": applicable}, indent=2, ensure_ascii=False), encoding="utf-8")
    rew = rewritable_languages or rm.get("rewritable_languages") or []
    # 做题语言必须 ≠ 原仓语言:排除原语言(含 c++/cpp、ts/typescript 等别名),否则候选可反推原仓。
    _ALIAS = {"cpp": "c++", "c++": "c++", "cxx": "c++", "ts": "typescript", "js": "javascript",
              "golang": "go", "py": "python", "rs": "rust", "c#": "csharp", "cs": "csharp"}
    def _norm_lang(l):
        return _ALIAS.get((l or "").strip().lower(), (l or "").strip().lower())
    _orig = _norm_lang(config.get("language") or rm.get("language"))
    rew = [l for l in rew if _norm_lang(l) != _orig]
    if not rew:                                            # 兜底:原列表全是原语言 -> 强制换一种主流语言
        rew = [l for l in ["rust", "go", "python"] if l != _orig] or ["rust"]
    (grader / "rewritable_languages.json").write_text(
        json.dumps({"rewritable_languages": rew}, indent=2, ensure_ascii=False), encoding="utf-8")

    # ---- 卷面 (visible) ----
    # issue 7: required language = rewritable_languages[0] (the curated choice). NEVER fall back to the
    # original repo's `language` -- exposing it gives the candidate a factor to reverse-infer the repo.
    gen = generation_language or (rew[0] if rew else "unknown")

    # contract + identity tokens already loaded/computed above; scrub the contract for the candidate side.
    scrubbed = _scrub_contract(contract, toks) if contract is not None else {}

    def S(text):
        return deident.scrub_text(text, toks)

    # req 2.7: name the security metrics that got tagged test cases (from the metrics table)
    sec_summary = [{"metric_id": mid, "name": metrics_idx.get(mid, {}).get("name", mid), "count": cnt}
                   for mid, cnt in sorted((emitted.get("security_by_metric") or {}).items())]

    (cand / "项目描述.md").write_text(S(_brief_md(rm.get("candidate_brief", ""))), encoding="utf-8")
    (cand / "用户API使用手册.md").write_text(S(_api_manual_md(scrubbed, scen)), encoding="utf-8")
    (cand / "功能模块文档.md").write_text(S(_modules_md(_load(repo_out / "03_modules.json", {}))), encoding="utf-8")
    (cand / "用户行为示例文档.md").write_text(S(_stories_md(_load(repo_out / "03_user-stories.json", {}))), encoding="utf-8")
    (cand / "非功能需求.md").write_text(S(_nfr_md(applicable, sec_summary)), encoding="utf-8")
    (cand / "generation_language.txt").write_text(gen + "\n", encoding="utf-8")
    (cand / "prompt.md").write_text(_prompt_md(gen, scen, config.get("dependencies")), encoding="utf-8")
    if contract_name and scrubbed:
        (cand / contract_name).write_text(
            json.dumps(scrubbed, indent=2, ensure_ascii=False), encoding="utf-8")

    report = {"grader_tests": n_tests, "applicable_metrics": len(applicable),
              "security_tests": emitted.get("n_security", 0), "security_by_metric": emitted.get("security_by_metric", {}),
              "smoke_tests": emitted.get("n_smoke", 0),
              "rewritable_languages": rew, "generation_language": gen,
              "candidate_files": sorted(p.name for p in cand.iterdir())}
    (exam / "package.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report
