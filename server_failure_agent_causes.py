#!/usr/bin/env python3
import collections
import json
import pathlib
import re

STATE = pathlib.Path("/mnt/yangh559/chuti-run")
GRADES = STATE / "grades"
LOGS = STATE / "logs"
SUBS = STATE / "submissions"

AGENTS = ["claude", "codex", "cursor", "kimi", "agy"]
MAIN = ["claude", "codex", "cursor", "kimi"]
EXCLUDE = {"dosisod-refurb"}
FUNC_KEY = "\u529f\u80fd\u5206"


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def read_text(path):
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def read_run_json(rid, agent):
    p = SUBS / rid / agent / "work" / "run.json"
    raw = read_text(p)
    try:
        obj = json.loads(raw) if raw.strip() else None
    except Exception as e:
        return {"exists": p.exists(), "parse_error": str(e), "raw": raw[:400]}
    return {"exists": p.exists(), "obj": obj, "raw": raw[:400]}


def launch_paths(run_info):
    obj = run_info.get("obj") or {}
    launch = obj.get("launch") if isinstance(obj, dict) else None
    if not isinstance(launch, list):
        return []
    return [str(x) for x in launch]


def classify(rid, agent, log, run_info):
    low = log.lower()
    launch = launch_paths(run_info)
    launch0 = launch[0] if launch else ""
    notes = []

    if not run_info.get("exists"):
        return "missing_run_json", "未交付 run.json"
    if run_info.get("parse_error"):
        return "invalid_run_json", f"run.json 不是合法 JSON: {run_info['parse_error']}"
    if not launch:
        return "invalid_run_json", "run.json 缺少 launch 数组"

    if "/tmp/exam_work/" in (run_info.get("raw") or "") or "/tmp/exam_work/" in log:
        if "bad interpreter" in low or "no such file or directory" in low or "not found" in low:
            return "non_relocatable_absolute_path", "交付物保留 /tmp/exam_work 绝对路径，回传后不可运行"

    if "bad interpreter" in low:
        return "non_relocatable_interpreter", "脚本或虚拟环境解释器路径不可迁移"

    if "json.decoder.jsondecodeerror" in low:
        if "_assert.py" in log or "json_canonical" in log or "normalized(" in log:
            return "invalid_output_format", "候选输出不是契约要求的合法 JSON/结构化格式"
        return "invalid_json_or_contract_file", "候选交付或输出中存在非法 JSON"

    if "[build.sh 非零退出" in log:
        if any(s in low for s in ["modulenotfounderror", "no module named", "pip:", "bad interpreter", "venv", ".venv"]):
            return "python_dependency_or_venv_failure", "Python 依赖/虚拟环境构建失败"
        if any(s in low for s in ["npm err", "pnpm", "yarn", "node-gyp", "package.json"]):
            return "node_dependency_or_build_failure", "Node/npm 依赖或构建失败"
        if any(s in low for s in ["error: could not compile", "cargo", "rustc"]):
            return "rust_compile_failure", "Rust/Cargo 编译失败"
        if any(s in low for s in ["go build", "go: ", "cannot find module", "go.mod"]):
            return "go_compile_failure", "Go 模块或编译失败"
        if any(s in low for s in ["gcc", "g++", "cmake", "make:", "ld:"]):
            return "native_compile_failure", "C/C++/native 构建失败"
        if any(s in low for s in ["could not resolve", "connection timed out", "connection refused", "certificate", "proxy"]):
            return "dependency_network_failure", "依赖下载或镜像访问失败"
        return "build_script_failed_other", "build.sh 非零退出，日志不足以细分生态"

    if any(s in low for s in ["permission denied", "is not executable"]):
        return "launch_permission_failure", "启动目标或脚本缺少执行权限"

    if "command not found" in low:
        return "missing_runtime_command", "run.json/build.sh 调用了不存在的命令"

    if "no such file or directory" in low or "not found" in low or "filenotfounderror" in low:
        if launch0:
            notes.append(f"launch[0]={launch0}")
        return "missing_launch_target", "run.json 指向的启动文件不存在或路径错误" + (f" ({'; '.join(notes)})" if notes else "")

    build_markers = ["build ok", "build complete", "finished release", "successfully built", "built "]
    if any(m in low for m in build_markers):
        return "smoke_or_startup_contract_failure", "构建完成，但 --help/smoke/启动健康检查未满足卷面契约"

    if not log.strip():
        return "empty_grade_log", "没有有效构建/启动日志，候选交付物未走到可判状态"

    return "unclassified_agent_delivery_failure", "候选交付物未通过 build/smoke 门，日志不足以进一步细分"


def concise_log(log):
    lines = [x for x in log.splitlines() if x.strip()]
    interesting = []
    pats = [
        "error", "failed", "not found", "no such file", "permission denied",
        "bad interpreter", "jsondecodeerror", "traceback", "build ok",
        "build complete", "nonzero", "非零",
    ]
    for line in lines:
        low = line.lower()
        if any(p in low for p in pats):
            interesting.append(line.strip())
    if not interesting:
        interesting = lines[:4]
    return " | ".join(interesting[:5])[:700]


def main():
    failures = []
    for rid_dir in sorted(GRADES.iterdir()):
        if not rid_dir.is_dir() or rid_dir.name in EXCLUDE:
            continue
        rid = rid_dir.name
        for agent in AGENTS:
            sc = load_json(rid_dir / agent / "score.json")
            if not isinstance(sc, dict) or sc.get("build_ok"):
                continue
            log = read_text(LOGS / f"grade-{rid}-{agent}.log")
            run_info = read_run_json(rid, agent)
            cause, detail = classify(rid, agent, log, run_info)
            failures.append({
                "rid": rid,
                "agent": agent,
                "cause": cause,
                "detail": detail,
                "func": sc.get(FUNC_KEY),
                "run": run_info.get("raw", "").replace("\n", " ")[:220],
                "evidence": concise_log(log),
            })

    by_agent = collections.Counter(f["agent"] for f in failures)
    by_cause = collections.Counter(f["cause"] for f in failures)
    main = [f for f in failures if f["agent"] in MAIN]
    main_by_agent = collections.Counter(f["agent"] for f in main)
    main_by_cause = collections.Counter(f["cause"] for f in main)
    by_agent_cause = {a: dict(collections.Counter(f["cause"] for f in failures if f["agent"] == a)) for a in AGENTS}

    examples = {}
    for f in failures:
        examples.setdefault(f["cause"], f)

    print(json.dumps({
        "total": len(failures),
        "by_agent": dict(by_agent),
        "by_cause": dict(by_cause),
        "main_total": len(main),
        "main_by_agent": dict(main_by_agent),
        "main_by_cause": dict(main_by_cause),
        "by_agent_cause": by_agent_cause,
        "examples": examples,
        "all_main_failures": main,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
