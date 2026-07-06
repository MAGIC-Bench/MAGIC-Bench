#!/usr/bin/env python3
import json
from pathlib import Path

SRC = Path("nfr_denominator_audit.json")
OUT_JSON = Path("nfr_corrected_summary.json")
OUT_MD = Path("nfr_corrected_summary.md")


def pct(n, d):
    return n / d if d else 0.0


def fmt(n, d):
    return f"{n}/{d} = {pct(n, d) * 100:.2f}%"


def row_obj(v):
    return {
        "reported": {
            "passed": v["reported_one"],
            "denominator": v["reported_den"],
            "rate": pct(v["reported_one"], v["reported_den"]),
        },
        "corrected_build_ok_only": {
            "passed": v["build_ok_true_one"],
            "denominator": v["build_ok_true_den"],
            "rate": pct(v["build_ok_true_one"], v["build_ok_true_den"]),
        },
        "removed_build_fail_denominator": v["build_ok_false_den"],
        "build_ok_true_none": v["build_ok_true_none"],
    }


def main():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    out = {"overall": {}, "agents": {}}
    for dim, v in data["overall"]["dimensions"].items():
        out["overall"][dim] = row_obj(v)
    for agent, av in data["agents"].items():
        out["agents"][agent] = {
            "projects": av["projects"],
            "build_fail": av["build_fail"],
            "dimensions": {dim: row_obj(v) for dim, v in av["dimensions"].items()},
        }
    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Corrected NFR Summary",
        "",
        "口径：只统计 `build_ok=true` 后实际测得的非 `None` NFR 指标；`build_ok=false` 后由硬门统一写入的 0 不进入 NFR 分母。",
        "",
        "## Overall",
        "",
        "| 维度 | 原报告口径 | 修正后口径 | 剔除的 build fail 分母 |",
        "|---|---:|---:|---:|",
    ]
    for dim, v in data["overall"]["dimensions"].items():
        lines.append(
            f"| {dim} | {fmt(v['reported_one'], v['reported_den'])} | "
            f"{fmt(v['build_ok_true_one'], v['build_ok_true_den'])} | {v['build_ok_false_den']} |"
        )
    lines.extend(["", "## By Agent", ""])
    for agent, av in data["agents"].items():
        lines.extend([
            f"### {agent}",
            "",
            f"- projects: {av['projects']}",
            f"- build_fail: {av['build_fail']}",
            "",
            "| 维度 | 原报告口径 | 修正后口径 | 剔除的 build fail 分母 |",
            "|---|---:|---:|---:|",
        ])
        for dim, v in av["dimensions"].items():
            lines.append(
                f"| {dim} | {fmt(v['reported_one'], v['reported_den'])} | "
                f"{fmt(v['build_ok_true_one'], v['build_ok_true_den'])} | {v['build_ok_false_den']} |"
            )
        lines.append("")
    OUT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT_JSON} and {OUT_MD}")


if __name__ == "__main__":
    main()
