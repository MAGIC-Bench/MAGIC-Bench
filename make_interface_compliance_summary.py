#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

SUMMARY = Path("cli_interface_compliance_summary.json")
ROWS = Path("cli_interface_all_project_summaries.json")
OUT = Path("cli_interface_compliance_summary.md")

AGENTS = ["claude", "codex", "cursor", "kimi"]
LABELS = {
    "claude": "Claude",
    "codex": "Codex",
    "cursor": "Cursor",
    "kimi": "Kimi",
}


def pct(v: float) -> str:
    return f"{v * 100:.2f}%"


def ratio(num: int, den: int) -> str:
    return f"{num}/{den} = {pct(num / den if den else 0.0)}"


def main() -> None:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    rows = json.loads(ROWS.read_text(encoding="utf-8"))
    build_ok_rows = [r for r in rows if r.get("build_ok")]
    overall_avg = (
        sum(float(r.get("interface_compliance", 0.0)) for r in build_ok_rows) / len(build_ok_rows)
        if build_ok_rows
        else 0.0
    )

    lines = [
        "# 接口符合度指标汇总",
        "",
        "生成时间：2026-07-01",
        "",
        "## 统计口径",
        "",
        "主口径只统计 `build_ok=true` 的仓库。构建失败的仓库不进入接口符合度分母；也就是说，如果某个模型 81 个仓库里只有 1 个构建成功，且该仓库接口探针全部通过，则该模型接口符合度按 `1/1` 计为满分。",
        "",
        "接口符合度 = 通过的 CLI 契约探针数 / 适用的 CLI 契约探针数。",
        "",
        "探针来自每个题目的 `02_cli-contract.json`，包括：",
        "",
        "- `--help`、短 help、`--version` 等基础可运行探针。",
        "- 未知选项应非零退出的拒绝探针。",
        "- help 文本中应出现 contract 声明的长选项、短选项、动作/子命令。",
        "",
        "## 主口径：仅构建成功仓库",
        "",
        "| 模型 | 构建成功仓库 | 接口探针通过率 | 平均项目接口符合度 | 完全符合项目数 |",
        "|---|---:|---:|---:|---:|",
    ]

    for agent in AGENTS:
        s = summary["agents"][agent]
        lines.append(
            "| {label} | {ok} | {probe} | {avg} | {full} |".format(
                label=LABELS[agent],
                ok=s["build_ok_projects"],
                probe=ratio(s["probe_passed_build_ok_only"], s["probe_total_build_ok_only"]),
                avg=pct(s["avg_project_compliance_build_ok_only"]),
                full=ratio(s["fully_compliant_projects"], s["build_ok_projects"]),
            )
        )

    overall = summary["overall"]
    lines.append(
        "| 主测合计 | {ok} | {probe} | {avg} | {full} |".format(
            ok=overall["build_ok_projects"],
            probe=ratio(overall["probe_passed_build_ok_only"], overall["probe_total_build_ok_only"]),
            avg=pct(overall_avg),
            full=ratio(overall["fully_compliant_projects"], overall["build_ok_projects"]),
        )
    )

    lines += [
        "",
        "## 参考口径：全量提交",
        "",
        "下表仅作补充参考。这里把构建失败仓库也放入分母，相当于把无法运行的提交视作接口探针全失败；它不作为 NFR/接口符合度的主统计口径。",
        "",
        "| 模型 | 全部仓库 | 构建失败仓库 | 全量接口探针通过率 |",
        "|---|---:|---:|---:|",
    ]
    for agent in AGENTS:
        s = summary["agents"][agent]
        lines.append(
            "| {label} | {projects} | {failed} | {probe} |".format(
                label=LABELS[agent],
                projects=s["projects"],
                failed=s["build_failed_projects"],
                probe=ratio(s["probe_passed"], s["probe_total"]),
            )
        )

    lines.append(
        "| 主测合计 | {projects} | {failed} | {probe} |".format(
            projects=overall["projects"],
            failed=overall["build_failed_projects"],
            probe=ratio(overall["probe_passed"], overall["probe_total"]),
        )
    )

    lines += [
        "",
        "## 数据文件",
        "",
        "- 汇总 JSON：`cli_interface_compliance_summary.json`",
        "- 逐仓库明细：`cli_interface_all_project_summaries.json`",
        "- 重跑探针脚本：`compute_cli_interface_compliance.py`",
    ]

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"OK -> {OUT}")


if __name__ == "__main__":
    main()
