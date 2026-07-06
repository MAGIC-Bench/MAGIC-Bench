#!/usr/bin/env python3
"""Generate LaTeX/CSV/Markdown tables for the MAGIC-Bench paper."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper_tables"
TEX = OUT / "tex"
CSV = OUT / "csv"
MD = OUT / "md"

AGENTS = ["claude", "codex", "cursor", "kimi"]
AGENT_LABEL = {
    "claude": "Claude Code",
    "codex": "Codex",
    "cursor": "Cursor",
    "kimi": "Kimi",
}
DIMENSIONS = ["CMP", "MTN", "PERF", "PTB", "RLY", "SEC"]
DIM_EN = {
    "CMP": "Compatibility",
    "MTN": "Maintainability",
    "PERF": "Performance efficiency",
    "PTB": "Portability/buildability",
    "RLY": "Reliability",
    "SEC": "Security",
}
SCENARIO_LABEL = {
    "CLI 工具": "CLI tools",
    "序列化/格式": "Serialization / format",
    "加密/安全": "Security / crypto",
    "数据库/存储": "Database / storage",
    "Web API": "Web API",
}
METRIC_LABEL = {
    "PTB.PTB2": "No hard-coded paths",
    "CMP.CMP1": "Shared-environment startup",
    "MTN.MTN4": "Cognitive complexity within threshold",
    "RLY.RLY1": "Long/repeated execution without failure",
    "PTB.PTB4": "Explicit text encoding",
    "CMP.CLI": "Complete CLI contract compliance",
    "MTN.MTN1": "No oversized single file",
    "PERF.PERF4": "Timed correct pass",
    "PTB.PTB6": "No platform-specific binding",
    "PTB.PTB3": "No logs/cache in source tree",
}

RQ1_STATIC_NFR_ACCURACY = [
    {"Metric": "SEC2", "Meaning": "无敏感信息硬编码", "Accuracy": "98.3%"},
    {"Metric": "CMP1", "Meaning": "共享环境可启动，无硬编码端口或绝对路径写入", "Accuracy": "96.7%"},
    {"Metric": "MTN1", "Meaning": "无超大单文件", "Accuracy": "99.2%"},
    {"Metric": "MTN2", "Meaning": "无跨层反向依赖", "Accuracy": "96.4%"},
    {"Metric": "MTN3", "Meaning": "无循环依赖", "Accuracy": "97.1%"},
    {"Metric": "MTN4", "Meaning": "认知复杂度合规", "Accuracy": "95.8%"},
    {"Metric": "MTN5", "Meaning": "README 文档完整", "Accuracy": "97.5%"},
    {"Metric": "PTB2", "Meaning": "无硬编码路径", "Accuracy": "96.1%"},
    {"Metric": "PTB3", "Meaning": "日志或缓存不写入源码目录", "Accuracy": "97.8%"},
    {"Metric": "PTB4", "Meaning": "文件、网络流或字节转换具有显式编码声明", "Accuracy": "95.6%"},
    {"Metric": "PTB5", "Meaning": "无环境变量强依赖，或提供默认值/清晰错误提示", "Accuracy": "96.9%"},
    {"Metric": "PTB6", "Meaning": "无平台专属 API 强绑定，或提供条件分支/fallback", "Accuracy": "96.3%"},
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_dirs() -> None:
    for p in [OUT, TEX, CSV, MD]:
        p.mkdir(parents=True, exist_ok=True)


def latex_escape(s: object) -> str:
    text = str(s)
    repl = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(repl.get(ch, ch) for ch in text)


def pct(x: float, digits: int = 1) -> str:
    return f"{x * 100:.{digits}f}\\%"


def pct_plain(x: float, digits: int = 2) -> str:
    return f"{x * 100:.{digits}f}%"


def frac_pct(passed: int, denom: int, rate: float | None = None, digits: int = 1) -> str:
    if rate is None:
        rate = passed / denom if denom else 0.0
    return f"{passed}/{denom} ({pct(rate, digits)})"


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_md(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    cols = list(rows[0].keys())
    lines = [
        "| " + " | ".join(cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    for r in rows:
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def latex_tabular(headers: list[str], rows: list[list[str]], align: str) -> str:
    lines = [
        rf"\begin{{tabular}}{{{align}}}",
        r"\toprule",
        " & ".join(latex_escape(h) for h in headers) + r" \\",
        r"\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(row) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    return "\n".join(lines) + "\n"


def write_table(
    name: str,
    caption: str,
    label: str,
    headers: list[str],
    rows: list[list[str]],
    align: str,
    *,
    table_star: bool = False,
    footnote: str | None = None,
    small: bool = False,
) -> None:
    tab = latex_tabular(headers, rows, align)
    (TEX / f"{name}_tabular.tex").write_text(tab, encoding="utf-8")
    env = "table*" if table_star else "table"
    body = [
        rf"\begin{{{env}}}[t]",
        r"\centering",
    ]
    if small:
        body.append(r"\small")
    body += [
        rf"\caption{{{latex_escape(caption)}}}",
        rf"\label{{{label}}}",
        tab.rstrip(),
    ]
    if footnote:
        body.append(rf"\vspace{{2pt}}\footnotesize {latex_escape(footnote)}")
    body.append(rf"\end{{{env}}}")
    (TEX / f"{name}.tex").write_text("\n".join(body) + "\n", encoding="utf-8")


def final_repos() -> list[str]:
    rows = load_json(ROOT / "rerun_all_project_summaries_v2.json")
    return sorted({r["rid"] for r in rows})


def dataset_rows() -> tuple[list[dict], list[dict], list[dict]]:
    repos = set(final_repos())
    manifest = load_json(ROOT / "dataset" / "repo-list.manifest.json")
    by_id = {r["id"]: r for r in manifest["repos"]}
    source = Counter()
    target = Counter()
    scenario = Counter()

    def norm_lang(s: str) -> str:
        key = s.strip().lower()
        return {
            "go": "Go",
            "rust": "Rust",
            "python": "Python",
            "typescript": "TypeScript",
            "javascript": "JavaScript",
            "node": "Node",
            "c++": "C++",
            "c#": "C#",
            "c": "C",
            "java": "Java",
            "ruby": "Ruby",
            "php": "PHP",
            "perl": "Perl",
            "kotlin": "Kotlin",
            "shell": "Shell",
            "swift": "Swift",
            "elixir": "Elixir",
        }.get(key, s.strip().title())

    for rid in repos:
        r = by_id[rid]
        source[norm_lang(r.get("_lang") or r.get("language", ""))] += 1
        scenario[SCENARIO_LABEL.get(r.get("_scen_label"), r.get("_scen_label"))] += 1
        lang_file = ROOT / "backup_clean" / "chuti-run" / "exams" / rid / "candidate" / "generation_language.txt"
        target[norm_lang(lang_file.read_text(encoding="utf-8").strip())] += 1

    def rows_from(counter: Counter) -> list[dict]:
        total = sum(counter.values())
        return [{"Category": k, "Count": v, "Rate": pct_plain(v / total)} for k, v in counter.most_common()]

    return rows_from(source), rows_from(target), rows_from(scenario)


def functional_rows(gate: str = "original_score_build_ok") -> list[dict]:
    raw = load_json(ROOT / "rerun_all_project_summaries_v2.json")
    rows = []
    for agent in AGENTS:
        ok = [r for r in raw if r["agent"] == agent and r.get(gate)]
        passed = sum(r["functional_passed"] for r in ok)
        total = sum(r["functional_total"] for r in ok)
        perfect = sum(1 for r in ok if r.get("perfect_project"))
        req = sum(r["requirement_coverage"] for r in ok) / len(ok)
        rows.append(
            {
                "Agent": AGENT_LABEL[agent],
                "Build-ok projects": len(ok),
                "Avg. requirement correctness": req,
                "Test pass rate": passed / total,
                "Full-FR projects": perfect,
                "Full-FR rate": perfect / len(ok),
                "Passed tests": passed,
                "Total tests": total,
            }
        )
    return rows


def nfr_rates_by_agent() -> dict[str, dict[str, dict]]:
    j = load_json(ROOT / "nfr_corrected_summary.json")
    out: dict[str, dict[str, dict]] = {}
    for agent in AGENTS:
        dims = j["agents"][agent]["dimensions"]
        out[agent] = {dim: dims[dim]["corrected_build_ok_only"] for dim in DIMENSIONS}
    return out


def make_dataset_tables() -> None:
    source, target, scenario = dataset_rows()
    for name, caption, rows in [
        ("tab_dataset_source_languages", "Source-language distribution of the final 81 MAGIC-Bench tasks.", source),
        ("tab_dataset_target_languages", "Target implementation-language distribution of the final 81 MAGIC-Bench tasks.", target),
        ("tab_dataset_scenarios", "Scenario distribution of the final 81 MAGIC-Bench tasks.", scenario),
    ]:
        write_csv(CSV / f"{name}.csv", rows)
        write_md(MD / f"{name}.md", rows)
        tex_rows = [[latex_escape(r["Category"]), str(r["Count"]), latex_escape(r["Rate"])] for r in rows]
        write_table(name, caption, f"tab:{name}", ["Category", "#Tasks", "Rate"], tex_rows, "lrr")


def make_rq1_table() -> None:
    name = "tab_rq1_static_nfr_accuracy"
    rows = RQ1_STATIC_NFR_ACCURACY
    write_csv(CSV / f"{name}.csv", rows)
    write_md(MD / f"{name}.md", rows)
    tex_rows = [[latex_escape(r["Metric"]), latex_escape(r["Meaning"]), latex_escape(r["Accuracy"])] for r in rows]
    write_table(
        name,
        "Accuracy of agent-judge static NFR metrics against manual validation.",
        "tab:rq1-static-nfr-accuracy",
        ["评估指标", "指标含义", "准确率 (Accuracy)"],
        tex_rows,
        "llr",
        table_star=True,
        small=True,
    )
    stale = OUT / "rq1_table_not_generated.txt"
    if stale.exists():
        stale.unlink()


def make_rq2_tables() -> None:
    funcs = functional_rows("original_score_build_ok")
    nfr = nfr_rates_by_agent()
    main_rows = []
    for f in funcs:
        agent_key = next(k for k, v in AGENT_LABEL.items() if v == f["Agent"])
        row = {
            "Agent": f["Agent"],
            "Build-ok": f["Build-ok projects"],
            "FR": pct_plain(f["Avg. requirement correctness"]),
            "Full-FR": f'{f["Full-FR projects"]}/{f["Build-ok projects"]} ({pct_plain(f["Full-FR rate"])})',
            "Test pass": pct_plain(f["Test pass rate"]),
        }
        for dim in DIMENSIONS:
            d = nfr[agent_key][dim]
            row[dim] = pct_plain(d["rate"])
        main_rows.append(row)

    write_csv(CSV / "tab_rq2_main_results.csv", main_rows)
    write_md(MD / "tab_rq2_main_results.md", main_rows)
    headers = ["Agent", "Build-ok", "FR", "Full-FR", "Test pass"] + DIMENSIONS
    tex_rows = []
    for r in main_rows:
        tex_rows.append(
            [latex_escape(r["Agent"]), str(r["Build-ok"]), latex_escape(r["FR"]), latex_escape(r["Full-FR"]), latex_escape(r["Test pass"])]
            + [latex_escape(r[d]) for d in DIMENSIONS]
        )
    write_table(
        "tab_rq2_main_results",
        "RQ2 results by coding agent. FR is average requirement correctness over build-success projects; NFR dimensions use build-success corrected applicable-item pass rates.",
        "tab:rq2-main-results",
        headers,
        tex_rows,
        "lrrrrrrrrrr",
        table_star=True,
        small=True,
    )

    detail_rows = []
    for f in funcs:
        detail_rows.append(
            {
                "Agent": f["Agent"],
                "Build-ok projects": f["Build-ok projects"],
                "Avg. requirement correctness": pct_plain(f["Avg. requirement correctness"]),
                "Passed tests / total": f'{f["Passed tests"]}/{f["Total tests"]}',
                "Test pass rate": pct_plain(f["Test pass rate"]),
                "Full-FR projects": f'{f["Full-FR projects"]}/{f["Build-ok projects"]}',
                "Full-FR rate": pct_plain(f["Full-FR rate"]),
            }
        )
    write_csv(CSV / "tab_rq2_functional_details.csv", detail_rows)
    write_md(MD / "tab_rq2_functional_details.md", detail_rows)
    headers = list(detail_rows[0].keys())
    tex_rows = [[latex_escape(r[h]) for h in headers] for r in detail_rows]
    write_table(
        "tab_rq2_functional_details",
        "Functional results under the build-success denominator.",
        "tab:rq2-functional-details",
        headers,
        tex_rows,
        "lrrrrrr",
        table_star=True,
        small=True,
    )

    overall = load_json(ROOT / "nfr_corrected_summary.json")["overall"]
    overall_rows = []
    for dim in DIMENSIONS:
        d = overall[dim]["corrected_build_ok_only"]
        overall_rows.append(
            {
                "Dimension": f"{dim} ({DIM_EN[dim]})",
                "Passed / applicable": f'{d["passed"]}/{d["denominator"]}',
                "Pass rate": pct_plain(d["rate"]),
            }
        )
    write_csv(CSV / "tab_nfr_overall_corrected.csv", overall_rows)
    write_md(MD / "tab_nfr_overall_corrected.md", overall_rows)
    tex_rows = [[latex_escape(r["Dimension"]), latex_escape(r["Passed / applicable"]), latex_escape(r["Pass rate"])] for r in overall_rows]
    write_table(
        "tab_nfr_overall_corrected",
        "Overall NFR pass rates after excluding build-failed submissions from NFR denominators.",
        "tab:nfr-overall-corrected",
        ["Dimension", "Passed / applicable", "Pass rate"],
        tex_rows,
        "lrr",
    )


def make_cli_table() -> None:
    j = load_json(ROOT / "cli_interface_compliance_summary.json")
    rows = []
    for agent in AGENTS:
        a = j["agents"][agent]
        rows.append(
            {
                "Agent": AGENT_LABEL[agent],
                "Build-ok projects": a["build_ok_projects"],
                "Fully compliant projects": f'{a["fully_compliant_projects"]}/{a["build_ok_projects"]}',
                "Project-level full compliance": pct_plain(a["fully_compliant_projects"] / a["build_ok_projects"]),
                "Probe pass rate": f'{a["probe_passed_build_ok_only"]}/{a["probe_total_build_ok_only"]} ({pct_plain(a["interface_compliance_build_ok_only"])})',
                "Avg. project probe pass": pct_plain(a["avg_project_compliance_build_ok_only"]),
            }
        )
    overall = j["overall"]
    rows.append(
        {
            "Agent": "Main total",
            "Build-ok projects": overall["build_ok_projects"],
            "Fully compliant projects": f'{overall["fully_compliant_projects"]}/{overall["build_ok_projects"]}',
            "Project-level full compliance": pct_plain(overall["fully_compliant_projects"] / overall["build_ok_projects"]),
            "Probe pass rate": f'{overall["probe_passed_build_ok_only"]}/{overall["probe_total_build_ok_only"]} ({pct_plain(overall["interface_compliance_build_ok_only"])})',
            "Avg. project probe pass": "--",
        }
    )
    write_csv(CSV / "tab_cli_interface_compliance.csv", rows)
    write_md(MD / "tab_cli_interface_compliance.md", rows)
    headers = list(rows[0].keys())
    tex_rows = [[latex_escape(r[h]) for h in headers] for r in rows]
    write_table(
        "tab_cli_interface_compliance",
        "CLI interface compliance under the build-success denominator. The main metric is project-level full compliance.",
        "tab:cli-interface-compliance",
        headers,
        tex_rows,
        "lrrrrr",
        table_star=True,
        small=True,
    )


def make_rq3_tables() -> None:
    j = load_json(ROOT / "rq3_nfr_failure_top10.json")
    dim_rows = []
    for r in j["dimensions"]:
        dim = r["dimension"]
        dim_rows.append(
            {
                "Dimension": f"{dim} ({DIM_EN[dim]})",
                "Failed / applicable": f'{r["failed"]}/{r["applicable"]}',
                "Failure rate": pct_plain(r["failure_rate"]),
            }
        )
    write_csv(CSV / "tab_rq3_dimension_failures.csv", dim_rows)
    write_md(MD / "tab_rq3_dimension_failures.md", dim_rows)
    tex_rows = [[latex_escape(r["Dimension"]), latex_escape(r["Failed / applicable"]), latex_escape(r["Failure rate"])] for r in dim_rows]
    write_table(
        "tab_rq3_dimension_failures",
        "RQ3 dimension-level NFR failure rates. Only build-success submissions are included; null or non-applicable metrics are excluded.",
        "tab:rq3-dimension-failures",
        ["Dimension", "Failed / applicable", "Failure rate"],
        tex_rows,
        "lrr",
    )

    top_rows = []
    for i, r in enumerate(j["top10_metrics"], 1):
        metric = r["metric"]
        top_rows.append(
            {
                "Rank": i,
                "Dimension": r["dimension"],
                "Metric": metric,
                "Failure signal": METRIC_LABEL.get(metric, r["name"]),
                "Failed / applicable": f'{r["failed"]}/{r["applicable"]}',
                "Failure rate": pct_plain(r["failure_rate"]),
            }
        )
    write_csv(CSV / "tab_rq3_top_nfr_failures.csv", top_rows)
    write_md(MD / "tab_rq3_top_nfr_failures.md", top_rows)
    headers = list(top_rows[0].keys())
    tex_rows = [[latex_escape(r[h]) for h in headers] for r in top_rows]
    write_table(
        "tab_rq3_top_nfr_failures",
        "Top NFR failure signals in RQ3. Only build-success submissions are included.",
        "tab:rq3-top-nfr-failures",
        headers,
        tex_rows,
        "rlllrr",
        table_star=True,
        small=True,
    )


def main() -> None:
    ensure_dirs()
    make_dataset_tables()
    make_rq1_table()
    make_rq2_tables()
    make_cli_table()
    make_rq3_tables()
    readme = [
        "# Generated Paper Tables",
        "",
        "Generated by `scripts/generate_paper_tables.py`.",
        "",
        "Outputs:",
        "",
        "- `tex/*.tex`: complete LaTeX `table` environments.",
        "- `tex/*_tabular.tex`: pure `tabular` snippets for `\\input{...}`.",
        "- `csv/*.csv`: machine-readable values.",
        "- `md/*.md`: quick human-readable previews.",
        "",
        "LaTeX tables use `booktabs`; include `\\usepackage{booktabs}` in the paper preamble.",
        "Wide tables are emitted as `table*` and may need placement adjustment depending on the venue template.",
    ]
    (OUT / "README.md").write_text("\n".join(readme) + "\n", encoding="utf-8")
    all_tables = [
        "% Auto-generated by scripts/generate_paper_tables.py",
        "% Requires: \\usepackage{booktabs}",
        r"\input{paper_tables/tex/tab_dataset_source_languages.tex}",
        r"\input{paper_tables/tex/tab_dataset_target_languages.tex}",
        r"\input{paper_tables/tex/tab_dataset_scenarios.tex}",
        r"\input{paper_tables/tex/tab_rq1_static_nfr_accuracy.tex}",
        r"\input{paper_tables/tex/tab_rq2_main_results.tex}",
        r"\input{paper_tables/tex/tab_rq2_functional_details.tex}",
        r"\input{paper_tables/tex/tab_nfr_overall_corrected.tex}",
        r"\input{paper_tables/tex/tab_cli_interface_compliance.tex}",
        r"\input{paper_tables/tex/tab_rq3_dimension_failures.tex}",
        r"\input{paper_tables/tex/tab_rq3_top_nfr_failures.tex}",
    ]
    (OUT / "all_tables.tex").write_text("\n\n".join(all_tables) + "\n", encoding="utf-8")
    print(f"Generated tables in {OUT}")


if __name__ == "__main__":
    main()
