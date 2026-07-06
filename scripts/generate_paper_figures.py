#!/usr/bin/env python3
"""Generate paper figures from MAGIC-Bench experiment data.

The script intentionally avoids matplotlib because the bundled runtime used by
this workspace does not include it. It emits both SVG vector figures and PNG
previews using Pillow.
"""

from __future__ import annotations

import csv
import html
import json
import math
from collections import Counter
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "paper_figures"

FIG_LANGUAGE_DISTRIBUTION = "语言分布饼图"
FIG_FUNCTIONAL_SUMMARY = "研究问题二-功能正确性结果"
FIG_SEVEN_DIMENSION = "研究问题二-七维指标结果"
FIG_RQ3_DIMENSION_FAILURES = "研究问题三-非功能维度失败率"
FIG_RQ3_TOP_FAILURES = "研究问题三-高频非功能失败指标"

AGENTS = ["claude", "codex", "cursor", "kimi"]
AGENT_LABEL = {
    "claude": "Claude Code",
    "codex": "Codex",
    "cursor": "Cursor",
    "kimi": "Kimi",
}
DIMENSIONS = ["FR", "CMP", "MTN", "PERF", "PTB", "RLY", "SEC"]
DIM_LABEL = {
    "FR": "FR",
    "CMP": "CMP",
    "MTN": "MTN",
    "PERF": "PERF",
    "PTB": "PTB",
    "RLY": "RLY",
    "SEC": "SEC",
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
    "PERF.PERF2": "Stable tail latency",
    "SEC.SEC2": "No hard-coded secrets",
    "SEC.SEC5": "SQL injection defense",
    "SEC.SEC1": "Unauthorized read blocked",
    "SEC.SEC4": "Unauthorized write blocked",
    "SEC.SEC3": "Sensitive fields encrypted",
}
SCENARIO_LABEL = {
    "CLI 工具": "CLI tools",
    "序列化/格式": "Serialization / format",
    "加密/安全": "Security / crypto",
    "数据库/存储": "Database / storage",
    "Web API": "Web API",
}

COLORS = [
    "#4E79A7",
    "#A0CBE8",
    "#F28E2B",
    "#59A14F",
    "#8CD17D",
    "#B6992D",
    "#499894",
    "#86BCB6",
    "#79706E",
    "#BAB0AC",
]
PAPER_BLUE = "#2F5D8C"
PAPER_GRAY = "#555555"
GRID = "#D7DCE2"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_out() -> None:
    OUT.mkdir(parents=True, exist_ok=True)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = []
    if bold:
        candidates += [
            Path(r"C:\Windows\Fonts\timesbd.ttf"),
            Path(r"C:\Windows\Fonts\cambriab.ttf"),
            Path(r"C:\Windows\Fonts\arialbd.ttf"),
            Path(r"C:\Windows\Fonts\calibrib.ttf"),
        ]
    candidates += [
        Path(r"C:\Windows\Fonts\times.ttf"),
        Path(r"C:\Windows\Fonts\cambria.ttc"),
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),
        Path(r"C:\Windows\Fonts\NotoSansSC-VF.ttf"),
        Path(r"C:\Windows\Fonts\simhei.ttf"),
    ]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size=size)
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_centered(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    fnt,
    fill: str = "#222222",
) -> None:
    w, h = text_size(draw, text, fnt)
    draw.text((xy[0] - w / 2, xy[1] - h / 2), text, font=fnt, fill=fill)


def save_svg(path: Path, width: int, height: int, elements: list[str]) -> None:
    body = "\n".join(elements)
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        f'<rect width="100%" height="100%" fill="white"/>\n{body}\n</svg>\n',
        encoding="utf-8",
    )


def svg_text(
    x: float,
    y: float,
    text: str,
    size: int = 16,
    weight: str = "normal",
    anchor: str = "start",
    fill: str = "#222222",
) -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-family="Times New Roman, Arial, Noto Sans SC, sans-serif" '
        f'font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" '
        f'fill="{fill}">{html.escape(text)}</text>'
    )


def svg_rect(x, y, w, h, fill, stroke="#ffffff", rx=0) -> str:
    return (
        f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
        f'rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="1"/>'
    )


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def collect_final_repos() -> list[str]:
    rows = load_json(ROOT / "rerun_all_project_summaries_v2.json")
    return sorted({r["rid"] for r in rows})


def collect_dataset_stats() -> tuple[list[dict], list[dict], list[dict]]:
    final_repos = set(collect_final_repos())
    manifest = load_json(ROOT / "dataset" / "repo-list.manifest.json")
    by_id = {r["id"]: r for r in manifest["repos"]}

    source_lang = Counter()
    scenario = Counter()
    target_lang = Counter()
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

    for rid in final_repos:
        row = by_id[rid]
        source_lang[norm_lang(row.get("_lang") or row.get("language", ""))] += 1
        scenario[SCENARIO_LABEL.get(row.get("_scen_label"), row.get("_scen_label"))] += 1
        lang_file = ROOT / "backup_clean" / "chuti-run" / "exams" / rid / "candidate" / "generation_language.txt"
        target_lang[norm_lang(lang_file.read_text(encoding="utf-8").strip())] += 1

    def rows_from_counter(kind: str, counter: Counter) -> list[dict]:
        total = sum(counter.values())
        return [
            {"kind": kind, "label": label, "count": count, "rate": count / total}
            for label, count in counter.most_common()
        ]

    return (
        rows_from_counter("source_language", source_lang),
        rows_from_counter("target_language", target_lang),
        rows_from_counter("scenario", scenario),
    )


def functional_by_agent(gate: str = "original_score_build_ok") -> list[dict]:
    rows = load_json(ROOT / "rerun_all_project_summaries_v2.json")
    out = []
    for agent in AGENTS:
        ok = [r for r in rows if r["agent"] == agent and r.get(gate)]
        if not ok:
            continue
        req = sum(r["requirement_coverage"] for r in ok) / len(ok)
        passed = sum(r["functional_passed"] for r in ok)
        total = sum(r["functional_total"] for r in ok)
        perfect = sum(1 for r in ok if r.get("perfect_project"))
        out.append(
            {
                "agent": AGENT_LABEL[agent],
                "build_ok_projects": len(ok),
                "avg_requirement_coverage": req,
                "test_pass_rate": passed / total if total else 0.0,
                "perfect_projects": perfect,
                "perfect_project_rate": perfect / len(ok),
                "test_passed": passed,
                "test_total": total,
            }
        )
    return out


def nfr_by_agent() -> dict[str, dict[str, float]]:
    j = load_json(ROOT / "nfr_corrected_summary.json")
    out: dict[str, dict[str, float]] = {}
    for agent in AGENTS:
        out[agent] = {}
        dims = j["agents"][agent]["dimensions"]
        for dim in ["CMP", "MTN", "PERF", "PTB", "RLY", "SEC"]:
            out[agent][dim] = dims[dim]["corrected_build_ok_only"]["rate"]
    return out


def seven_dimension_rows() -> list[dict]:
    fr_rows = functional_by_agent("original_score_build_ok")
    fr = {r["agent"]: r["avg_requirement_coverage"] for r in fr_rows}
    nfr = nfr_by_agent()
    rows = []
    for agent in AGENTS:
        label = AGENT_LABEL[agent]
        row = {"agent": label, "FR": fr[label]}
        row.update({dim: nfr[agent][dim] for dim in ["CMP", "MTN", "PERF", "PTB", "RLY", "SEC"]})
        rows.append(row)
    return rows


def draw_horizontal_bars(
    rows: list[dict],
    title: str,
    subtitle: str,
    out_name: str,
    value_key: str = "count",
    label_key: str = "label",
    value_is_rate: bool = False,
    width: int = 1100,
    height: int | None = None,
    margin_l: int = 260,
) -> None:
    if height is None:
        height = 170 + len(rows) * 42
    margin_r, margin_t, margin_b = 80, 105, 60
    plot_w = width - margin_l - margin_r
    bar_h = 24
    gap = 18
    max_v = max(float(r[value_key]) for r in rows) or 1

    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    title_f = font(28, bold=True)
    sub_f = font(17)
    label_f = font(16)
    small_f = font(14)
    d.text((40, 28), title, font=title_f, fill="#202020")
    d.text((40, 66), subtitle, font=sub_f, fill="#555555")

    svg = [
        svg_text(40, 52, title, 28, "bold"),
        svg_text(40, 88, subtitle, 17, fill="#555555"),
    ]
    for i, r in enumerate(rows):
        y = margin_t + i * (bar_h + gap)
        label = str(r[label_key])
        v = float(r[value_key])
        bw = plot_w * v / max_v
        color = COLORS[i % len(COLORS)]
        d.text((40, y + 2), label, font=label_f, fill="#222222")
        d.rounded_rectangle((margin_l, y, margin_l + plot_w, y + bar_h), radius=4, fill="#ECEFF3")
        d.rounded_rectangle((margin_l, y, margin_l + bw, y + bar_h), radius=4, fill=color)
        val = pct(v) if value_is_rate else f"{int(v)}"
        d.text((margin_l + bw + 10, y + 2), val, font=small_f, fill="#222222")
        svg += [
            svg_text(40, y + 18, label, 16),
            svg_rect(margin_l, y, plot_w, bar_h, "#ECEFF3", rx=4),
            svg_rect(margin_l, y, bw, bar_h, color, rx=4),
            svg_text(margin_l + bw + 10, y + 18, val, 14),
        ]

    img.save(OUT / f"{out_name}.png")
    save_svg(OUT / f"{out_name}.svg", width, height, svg)


def draw_language_distribution(source_rows: list[dict], target_rows: list[dict]) -> None:
    # Keep the long-tail visible but compact.
    source_top = source_rows[:10]
    other_count = sum(r["count"] for r in source_rows[10:])
    if other_count:
        total = sum(r["count"] for r in source_rows)
        source_top.append({"kind": "source_language", "label": "Other", "count": other_count, "rate": other_count / total})
    draw_horizontal_bars(
        source_top,
        "Source Repository Languages",
        "Final 81 MAGIC-Bench tasks; long-tail languages grouped as Other.",
        "fig_dataset_source_languages",
    )
    draw_horizontal_bars(
        target_rows,
        "Target Implementation Languages",
        "Language required in candidate-facing tasks.",
        "fig_dataset_target_languages",
    )


def draw_functional_summary(rows: list[dict]) -> None:
    width, height = 1120, 620
    margin_l, margin_r, margin_t, margin_b = 90, 70, 105, 90
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b
    max_v = 0.8
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    title_f, sub_f, axis_f, small_f = font(28, True), font(17), font(15), font(13)
    d.text((40, 28), "Functional Results by Agent", font=title_f, fill="#202020")
    d.text((40, 66), "Build-success denominator; labels show perfect projects.", font=sub_f, fill="#555555")

    svg = [
        svg_text(40, 52, "Functional Results by Agent", 28, "bold"),
        svg_text(40, 88, "Build-success denominator; labels show perfect projects.", 17, fill="#555555"),
    ]
    # Axes/grid.
    for tick in [0, 0.2, 0.4, 0.6, 0.8]:
        y = margin_t + plot_h * (1 - tick / max_v)
        d.line((margin_l, y, width - margin_r, y), fill="#E6E8EB", width=1)
        d.text((38, y - 8), f"{int(tick*100)}%", font=axis_f, fill="#666666")
        svg.append(f'<line x1="{margin_l}" y1="{y:.1f}" x2="{width-margin_r}" y2="{y:.1f}" stroke="#E6E8EB"/>')
        svg.append(svg_text(45, y + 5, f"{int(tick*100)}%", 15, anchor="middle", fill="#666666"))
    d.line((margin_l, margin_t, margin_l, margin_t + plot_h), fill="#444444", width=1)
    d.line((margin_l, margin_t + plot_h, width - margin_r, margin_t + plot_h), fill="#444444", width=1)

    group_w = plot_w / len(rows)
    bar_w = 48
    series = [
        ("Avg requirement coverage", "avg_requirement_coverage", "#2E86AB"),
        ("Test pass rate", "test_pass_rate", "#F18F01"),
        ("Perfect project rate", "perfect_project_rate", "#3B9A59"),
    ]
    for i, r in enumerate(rows):
        cx = margin_l + group_w * i + group_w / 2
        for j, (_, key, color) in enumerate(series):
            x = cx + (j - 1) * (bar_w + 8) - bar_w / 2
            v = float(r[key])
            h = plot_h * min(v, max_v) / max_v
            y = margin_t + plot_h - h
            d.rounded_rectangle((x, y, x + bar_w, margin_t + plot_h), radius=4, fill=color)
            d.text((x - 3, y - 18), pct(v), font=small_f, fill="#222222")
            svg.append(svg_rect(x, y, bar_w, h, color, rx=4))
            svg.append(svg_text(x + bar_w / 2, y - 6, pct(v), 13, anchor="middle"))
        draw_centered(d, (cx, margin_t + plot_h + 26), r["agent"], axis_f)
        draw_centered(d, (cx, margin_t + plot_h + 48), f"perfect={r['perfect_projects']}/{r['build_ok_projects']}", small_f, "#555555")
        svg.append(svg_text(cx, margin_t + plot_h + 32, r["agent"], 15, anchor="middle"))
        svg.append(svg_text(cx, margin_t + plot_h + 54, f"perfect={r['perfect_projects']}/{r['build_ok_projects']}", 13, anchor="middle", fill="#555555"))

    # Legend.
    lx, ly = width - 470, 34
    for i, (name, _, color) in enumerate(series):
        x = lx
        y = ly + i * 24
        d.rectangle((x, y, x + 16, y + 16), fill=color)
        d.text((x + 24, y - 1), name, font=small_f, fill="#222222")
        svg.append(svg_rect(x, y, 16, 16, color))
        svg.append(svg_text(x + 24, y + 13, name, 13))

    img.save(OUT / "fig_rq2_functional_summary.png")
    save_svg(OUT / "fig_rq2_functional_summary.svg", width, height, svg)


def heat_color(value: float) -> str:
    # Light warm gray to saturated teal-blue.
    lo = (244, 241, 234)
    hi = (37, 116, 169)
    t = max(0.0, min(1.0, value))
    rgb = tuple(round(lo[i] + (hi[i] - lo[i]) * t) for i in range(3))
    return "#%02x%02x%02x" % rgb


def draw_heatmap(rows: list[dict]) -> None:
    width, height = 1040, 520
    margin_l, margin_t = 160, 110
    cell_w, cell_h = 112, 68
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    title_f, sub_f, label_f, val_f = font(28, True), font(17), font(15), font(16, True)
    d.text((40, 28), "Seven-Dimensional Results", font=title_f, fill="#202020")
    d.text((40, 66), "FR uses average requirement coverage; NFR dimensions use build-success corrected pass rates.", font=sub_f, fill="#555555")

    svg = [
        svg_text(40, 52, "Seven-Dimensional Results", 28, "bold"),
        svg_text(40, 88, "FR uses average requirement coverage; NFR dimensions use build-success corrected pass rates.", 17, fill="#555555"),
    ]
    for j, dim in enumerate(DIMENSIONS):
        x = margin_l + j * cell_w + cell_w / 2
        draw_centered(d, (x, margin_t - 24), DIM_LABEL[dim], label_f)
        svg.append(svg_text(x, margin_t - 18, DIM_LABEL[dim], 15, anchor="middle"))
    for i, r in enumerate(rows):
        y = margin_t + i * cell_h
        d.text((40, y + cell_h / 2 - 8), r["agent"], font=label_f, fill="#222222")
        svg.append(svg_text(40, y + cell_h / 2 + 6, r["agent"], 15))
        for j, dim in enumerate(DIMENSIONS):
            x = margin_l + j * cell_w
            v = float(r[dim])
            color = heat_color(v)
            text_fill = "white" if v >= 0.55 else "#222222"
            d.rounded_rectangle((x, y, x + cell_w - 4, y + cell_h - 4), radius=4, fill=color, outline="white")
            draw_centered(d, (x + cell_w / 2 - 2, y + cell_h / 2 - 2), pct(v), val_f, text_fill)
            svg.append(svg_rect(x, y, cell_w - 4, cell_h - 4, color, rx=4))
            svg.append(svg_text(x + cell_w / 2 - 2, y + cell_h / 2 + 5, pct(v), 16, "bold", "middle", text_fill))

    img.save(OUT / "fig_rq2_seven_dimension_heatmap.png")
    save_svg(OUT / "fig_rq2_seven_dimension_heatmap.svg", width, height, svg)


def draw_method_framework() -> None:
    width, height = 1240, 390
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    title_f, box_f, small_f = font(28, True), font(15, True), font(13)
    d.text((40, 28), "MAGIC-Bench Evaluation Workflow", font=title_f, fill="#202020")
    svg = [svg_text(40, 52, "MAGIC-Bench Evaluation Workflow", 28, "bold")]
    boxes = [
        ("Real OSS\nprojects", 60, 145, "#2E86AB"),
        ("De-identified\nrequirements", 245, 145, "#6A4C93"),
        ("Coding\nagents", 430, 145, "#F18F01"),
        ("Generated\nprojects", 615, 145, "#3B9A59"),
        ("Hidden\nblack-box grader", 800, 145, "#D1495B"),
        ("Multi-dimensional\nscores", 1000, 145, "#4B5D67"),
    ]
    bw, bh = 150, 84
    for text, x, y, color in boxes:
        d.rounded_rectangle((x, y, x + bw, y + bh), radius=8, fill=color)
        svg.append(svg_rect(x, y, bw, bh, color, rx=8))
        lines = text.split("\n")
        for k, line in enumerate(lines):
            yy = y + 32 + k * 22
            draw_centered(d, (x + bw / 2, yy), line, box_f, "white")
            svg.append(svg_text(x + bw / 2, yy + 5, line, 15, "bold", "middle", "white"))
    # Arrows.
    for (_, x, y, _), (_, nx, ny, _) in zip(boxes, boxes[1:]):
        x1, x2, yy = x + bw + 12, nx - 12, y + bh / 2
        d.line((x1, yy, x2, yy), fill="#444444", width=3)
        d.polygon([(x2, yy), (x2 - 10, yy - 6), (x2 - 10, yy + 6)], fill="#444444")
        svg.append(f'<line x1="{x1}" y1="{yy}" x2="{x2}" y2="{yy}" stroke="#444444" stroke-width="3"/>')
        svg.append(f'<polygon points="{x2},{yy} {x2-10},{yy-6} {x2-10},{yy+6}" fill="#444444"/>')
    # Reference oracle branch.
    d.rounded_rectangle((615, 270, 150 + 615, 335), radius=8, fill="#ECEFF3", outline="#777777")
    draw_centered(d, (690, 302), "Reference execution\nfreezes golden behavior", small_f, "#222222")
    d.line((690, 270, 690, 235), fill="#777777", width=2)
    d.line((765, 302, 792, 188), fill="#777777", width=2)
    svg.append(svg_rect(615, 270, 150, 65, "#ECEFF3", "#777777", rx=8))
    svg.append(svg_text(690, 294, "Reference execution", 13, anchor="middle"))
    svg.append(svg_text(690, 314, "freezes golden behavior", 13, anchor="middle"))
    svg.append('<line x1="690" y1="270" x2="690" y2="235" stroke="#777777" stroke-width="2"/>')
    svg.append('<line x1="765" y1="302" x2="792" y2="188" stroke="#777777" stroke-width="2"/>')
    img.save(OUT / "fig_method_framework.png")
    save_svg(OUT / "fig_method_framework.svg", width, height, svg)


def draw_rq3_top_failures(rows: list[dict]) -> None:
    data = [
        {
            "label": r["metric"].replace(".", " ") + "  " + METRIC_LABEL.get(r["metric"], r["name"]),
            "failed": r["failed"],
            "applicable": r["applicable"],
            "failure_rate": r["failure_rate"],
        }
        for r in rows
    ]
    draw_horizontal_bars(
        data,
        "Top NFR Failure Signals",
        "Build-success submissions only; bars show failure rate.",
        "fig_rq3_top_nfr_failures",
        value_key="failure_rate",
        value_is_rate=True,
        width=1460,
        height=610,
        margin_l=500,
    )


def draw_rq3_dimension_failures(rows: list[dict]) -> None:
    data = [
        {
            "label": f"{r['dimension']} ({english_dimension(r['dimension'])})",
            "failure_rate": r["failure_rate"],
            "failed": r["failed"],
            "applicable": r["applicable"],
        }
        for r in rows
    ]
    draw_horizontal_bars(
        data,
        "NFR Failure Rate by Dimension",
        "Build-success submissions only; null or non-applicable metrics excluded.",
        "fig_rq3_dimension_failures",
        value_key="failure_rate",
        value_is_rate=True,
        width=1080,
        height=440,
    )


def english_dimension(dim: str) -> str:
    return {
        "CMP": "Compatibility",
        "MTN": "Maintainability",
        "PERF": "Performance",
        "PTB": "Portability/build",
        "RLY": "Reliability",
        "SEC": "Security",
    }.get(dim, dim)


def clean_old_figures() -> None:
    """Remove stale generated figures so the directory reflects current needs."""
    for pattern in [
        "fig_*.png",
        "fig_*.svg",
        "图*.png",
        "图*.svg",
        "语言*.png",
        "语言*.svg",
        "研究问题*.png",
        "研究问题*.svg",
    ]:
        for path in OUT.glob(pattern):
            path.unlink()


def pie_path(cx: float, cy: float, ro: float, ri: float, start: float, end: float) -> str:
    def pt(r: float, deg: float) -> tuple[float, float]:
        a = math.radians(deg - 90)
        return cx + r * math.cos(a), cy + r * math.sin(a)

    x1, y1 = pt(ro, start)
    x2, y2 = pt(ro, end)
    x3, y3 = pt(ri, end)
    x4, y4 = pt(ri, start)
    large = 1 if end - start > 180 else 0
    return (
        f'M {x1:.2f} {y1:.2f} '
        f'A {ro:.2f} {ro:.2f} 0 {large} 1 {x2:.2f} {y2:.2f} '
        f'L {x3:.2f} {y3:.2f} '
        f'A {ri:.2f} {ri:.2f} 0 {large} 0 {x4:.2f} {y4:.2f} Z'
    )


def compact_language_rows(rows: list[dict], top_n: int) -> list[dict]:
    head = rows[:top_n]
    other_count = sum(r["count"] for r in rows[top_n:])
    if other_count:
        total = sum(r["count"] for r in rows)
        head = head + [{"kind": rows[0]["kind"], "label": "Other", "count": other_count, "rate": other_count / total}]
    return head


def draw_donut_pair(source_rows: list[dict], target_rows: list[dict]) -> None:
    source = compact_language_rows(source_rows, 6)
    target = compact_language_rows(target_rows, 5)
    width, height = 1160, 500
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    label_f, small_f = font(14), font(13)
    svg = []

    def draw_one(rows: list[dict], cx: int, cy: int, heading: str, legend_x: int) -> None:
        total = sum(r["count"] for r in rows)
        start = 0.0
        ro, ri = 118, 58
        d.text((cx - 100, 44), heading, font=font(18, True), fill="#111111")
        svg.append(svg_text(cx, 62, heading, 18, "bold", "middle", "#111111"))
        for i, r in enumerate(rows):
            extent = 360 * r["count"] / total
            color = COLORS[i % len(COLORS)]
            d.pieslice((cx - ro, cy - ro, cx + ro, cy + ro), start - 90, start + extent - 90, fill=color, outline="white", width=1)
            svg.append(f'<path d="{pie_path(cx, cy, ro, ri, start, start + extent)}" fill="{color}" stroke="white" stroke-width="1"/>')
            start += extent
        d.ellipse((cx - ri, cy - ri, cx + ri, cy + ri), fill="white", outline="white")
        svg.append(f'<circle cx="{cx}" cy="{cy}" r="{ri}" fill="white"/>')
        draw_centered(d, (cx, cy - 8), str(total), font(22, True), "#111111")
        draw_centered(d, (cx, cy + 18), "tasks", small_f, "#555555")
        svg.append(svg_text(cx, cy - 2, str(total), 22, "bold", "middle", "#111111"))
        svg.append(svg_text(cx, cy + 24, "tasks", 13, anchor="middle", fill="#555555"))
        ly = 96
        for i, r in enumerate(rows):
            y = ly + i * 34
            color = COLORS[i % len(COLORS)]
            d.rectangle((legend_x, y, legend_x + 15, y + 15), fill=color)
            label = f"{r['label']}  {r['count']} ({r['rate']*100:.1f}%)"
            d.text((legend_x + 24, y - 2), label, font=label_f, fill="#222222")
            svg.append(svg_rect(legend_x, y, 15, 15, color, stroke=color))
            svg.append(svg_text(legend_x + 24, y + 12, label, 14))

    draw_one(source, 235, 252, "Source repositories", 390)
    draw_one(target, 760, 252, "Target languages", 900)
    img.save(OUT / f"{FIG_LANGUAGE_DISTRIBUTION}.png")
    save_svg(OUT / f"{FIG_LANGUAGE_DISTRIBUTION}.svg", width, height, svg)


def draw_paper_horizontal_rate_bars(
    rows: list[dict],
    title: str,
    subtitle: str,
    out_name: str,
    label_key: str = "label",
    value_key: str = "failure_rate",
    width: int = 1120,
    height: int | None = None,
    margin_l: int = 420,
) -> None:
    if height is None:
        height = 130 + len(rows) * 36
    margin_t, margin_r, margin_b = 44, 70, 55
    plot_w = width - margin_l - margin_r
    plot_h = height - margin_t - margin_b
    max_v = 1.0
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    label_f, small_f = font(13), font(12)
    svg = []
    for tick in [0, 0.25, 0.5, 0.75, 1.0]:
        x = margin_l + plot_w * tick / max_v
        d.line((x, margin_t - 8, x, margin_t + plot_h), fill=GRID, width=1)
        d.text((x - 12, margin_t + plot_h + 12), f"{int(tick*100)}", font=small_f, fill="#555555")
        svg.append(f'<line x1="{x:.1f}" y1="{margin_t-8}" x2="{x:.1f}" y2="{margin_t+plot_h}" stroke="{GRID}" stroke-width="1"/>')
        svg.append(svg_text(x, margin_t + plot_h + 28, f"{int(tick*100)}", 12, anchor="middle", fill="#555555"))
    d.text((margin_l + plot_w / 2 - 20, height - 18), "Failure rate (%)", font=small_f, fill="#333333")
    svg.append(svg_text(margin_l + plot_w / 2, height - 4, "Failure rate (%)", 12, anchor="middle"))
    bar_h = 15
    row_gap = plot_h / len(rows)
    for i, r in enumerate(rows):
        y = margin_t + i * row_gap + (row_gap - bar_h) / 2
        label = str(r[label_key])
        v = float(r[value_key])
        bw = plot_w * v / max_v
        d.text((40, y - 1), label, font=label_f, fill="#222222")
        d.rectangle((margin_l, y, margin_l + bw, y + bar_h), fill=PAPER_BLUE)
        d.text((margin_l + bw + 8, y - 1), pct(v), font=small_f, fill="#222222")
        svg.append(svg_text(40, y + 12, label, 13))
        svg.append(svg_rect(margin_l, y, bw, bar_h, PAPER_BLUE, stroke=PAPER_BLUE))
        svg.append(svg_text(margin_l + bw + 8, y + 12, pct(v), 12))
    img.save(OUT / f"{out_name}.png")
    save_svg(OUT / f"{out_name}.svg", width, height, svg)


def draw_rq3_top_failures_paper(rows: list[dict]) -> None:
    data = [
        {
            "label": f"{r['metric'].split('.')[-1]}: {METRIC_LABEL.get(r['metric'], r['name'])}",
            "failure_rate": r["failure_rate"],
        }
        for r in rows
    ]
    draw_paper_horizontal_rate_bars(
        data,
        "Top NFR Failure Signals",
        "Build-success submissions only; null or non-applicable metrics excluded.",
        FIG_RQ3_TOP_FAILURES,
        width=1320,
        height=470,
        margin_l=470,
    )


def draw_rq3_dimension_failures_paper(rows: list[dict]) -> None:
    data = [
        {"label": f"{r['dimension']} ({english_dimension(r['dimension'])})", "failure_rate": r["failure_rate"]}
        for r in rows
    ]
    draw_paper_horizontal_rate_bars(
        data,
        "NFR Failure Rate by Dimension",
        "Build-success submissions only.",
        FIG_RQ3_DIMENSION_FAILURES,
        width=1040,
        height=340,
        margin_l=290,
    )


def draw_functional_summary_paper(rows: list[dict]) -> None:
    width, height = 1030, 470
    margin_l, margin_r, margin_t, margin_b = 76, 38, 48, 82
    plot_w, plot_h = width - margin_l - margin_r, height - margin_t - margin_b
    max_v = 0.8
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    axis_f, small_f = font(12), font(11)
    svg = []
    for tick in [0, 0.2, 0.4, 0.6, 0.8]:
        y = margin_t + plot_h * (1 - tick / max_v)
        d.line((margin_l, y, width - margin_r, y), fill=GRID, width=1)
        d.text((30, y - 7), f"{int(tick*100)}", font=axis_f, fill="#555555")
        svg.append(f'<line x1="{margin_l}" y1="{y:.1f}" x2="{width-margin_r}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
        svg.append(svg_text(44, y + 4, f"{int(tick*100)}", 12, anchor="middle", fill="#555555"))
    d.line((margin_l, margin_t, margin_l, margin_t + plot_h), fill="#222222", width=1)
    d.line((margin_l, margin_t + plot_h, width - margin_r, margin_t + plot_h), fill="#222222", width=1)
    d.text((20, 86), "%", font=axis_f, fill="#333333")
    svg.append(svg_text(24, 86, "%", 12, fill="#333333"))
    series = [
        ("Requirement coverage", "avg_requirement_coverage", "#2F5D8C"),
        ("Test pass", "test_pass_rate", "#8E8E8E"),
        ("Full-FR", "perfect_project_rate", "#B0B0B0"),
    ]
    group_w = plot_w / len(rows)
    bar_w = 38
    for i, r in enumerate(rows):
        cx = margin_l + i * group_w + group_w / 2
        for j, (_, key, color) in enumerate(series):
            x = cx + (j - 1) * (bar_w + 7) - bar_w / 2
            v = float(r[key])
            h = plot_h * min(v, max_v) / max_v
            y = margin_t + plot_h - h
            d.rectangle((x, y, x + bar_w, margin_t + plot_h), fill=color)
            d.text((x - 2, y - 14), pct(v), font=small_f, fill="#111111")
            svg.append(svg_rect(x, y, bar_w, h, color, stroke=color))
            svg.append(svg_text(x + bar_w / 2, y - 3, pct(v), 11, anchor="middle"))
        draw_centered(d, (cx, margin_t + plot_h + 24), r["agent"], axis_f)
        draw_centered(d, (cx, margin_t + plot_h + 43), f"{r['perfect_projects']}/{r['build_ok_projects']} full", small_f, "#555555")
        svg.append(svg_text(cx, margin_t + plot_h + 30, r["agent"], 12, anchor="middle"))
        svg.append(svg_text(cx, margin_t + plot_h + 49, f"{r['perfect_projects']}/{r['build_ok_projects']} full", 11, anchor="middle", fill="#555555"))
    lx, ly = width - 310, 26
    for i, (name, _, color) in enumerate(series):
        y = ly + i * 20
        d.rectangle((lx, y, lx + 14, y + 14), fill=color)
        d.text((lx + 22, y - 1), name, font=small_f, fill="#222222")
        svg.append(svg_rect(lx, y, 14, 14, color, stroke=color))
        svg.append(svg_text(lx + 22, y + 12, name, 11))
    img.save(OUT / f"{FIG_FUNCTIONAL_SUMMARY}.png")
    save_svg(OUT / f"{FIG_FUNCTIONAL_SUMMARY}.svg", width, height, svg)


def draw_seven_dimension_lineplot(rows: list[dict]) -> None:
    width, height = 1060, 470
    margin_l, margin_r, margin_t, margin_b = 76, 42, 48, 78
    plot_w, plot_h = width - margin_l - margin_r, height - margin_t - margin_b
    img = Image.new("RGB", (width, height), "white")
    d = ImageDraw.Draw(img)
    label_f, small_f = font(12), font(11)
    svg = []
    for tick in [0, 0.25, 0.5, 0.75, 1.0]:
        y = margin_t + plot_h * (1 - tick)
        d.line((margin_l, y, width - margin_r, y), fill=GRID, width=1)
        d.text((30, y - 7), f"{int(tick*100)}", font=label_f, fill="#555555")
        svg.append(f'<line x1="{margin_l}" y1="{y:.1f}" x2="{width-margin_r}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
        svg.append(svg_text(44, y + 4, f"{int(tick*100)}", 12, anchor="middle", fill="#555555"))
    d.line((margin_l, margin_t, margin_l, margin_t + plot_h), fill="#222222", width=1)
    d.line((margin_l, margin_t + plot_h, width - margin_r, margin_t + plot_h), fill="#222222", width=1)
    xs = [margin_l + i * plot_w / (len(DIMENSIONS) - 1) for i in range(len(DIMENSIONS))]
    for x, dim in zip(xs, DIMENSIONS):
        draw_centered(d, (x, margin_t + plot_h + 22), dim, label_f)
        svg.append(svg_text(x, margin_t + plot_h + 28, dim, 12, anchor="middle"))
    line_colors = ["#2F5D8C", "#555555", "#9C6B30", "#5A7D5A"]
    for idx, r in enumerate(rows):
        pts = []
        for x, dim in zip(xs, DIMENSIONS):
            v = float(r[dim])
            y = margin_t + plot_h * (1 - v)
            pts.append((x, y))
        color = line_colors[idx]
        d.line(pts, fill=color, width=2)
        svg.append('<polyline points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in pts) + f'" fill="none" stroke="{color}" stroke-width="2"/>')
        for x, y in pts:
            d.ellipse((x - 4, y - 4, x + 4, y + 4), fill="white", outline=color, width=2)
            svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="white" stroke="{color}" stroke-width="2"/>')
    lx, ly = width - 220, 106
    for idx, r in enumerate(rows):
        color = line_colors[idx]
        y = ly + idx * 23
        d.line((lx, y + 6, lx + 28, y + 6), fill=color, width=2)
        d.ellipse((lx + 10, y + 2, lx + 18, y + 10), fill="white", outline=color, width=2)
        d.text((lx + 38, y - 2), r["agent"], font=small_f, fill="#222222")
        svg.append(f'<line x1="{lx}" y1="{y+6}" x2="{lx+28}" y2="{y+6}" stroke="{color}" stroke-width="2"/>')
        svg.append(f'<circle cx="{lx+14}" cy="{y+6}" r="4" fill="white" stroke="{color}" stroke-width="2"/>')
        svg.append(svg_text(lx + 38, y + 9, r["agent"], 11))
    img.save(OUT / f"{FIG_SEVEN_DIMENSION}.png")
    save_svg(OUT / f"{FIG_SEVEN_DIMENSION}.svg", width, height, svg)


def main() -> None:
    ensure_out()
    clean_old_figures()

    source_lang, target_lang, scenario = collect_dataset_stats()
    write_csv(OUT / "dataset_source_languages.csv", source_lang)
    write_csv(OUT / "dataset_target_languages.csv", target_lang)
    write_csv(OUT / "dataset_scenarios.csv", scenario)
    draw_donut_pair(source_lang, target_lang)

    func = functional_by_agent("original_score_build_ok")
    func_rerun = functional_by_agent("rerun_build_gate_ok")
    write_csv(OUT / "rq2_functional_by_agent_original_build_ok.csv", func)
    write_csv(OUT / "rq2_functional_by_agent_rerun_build_ok.csv", func_rerun)
    draw_functional_summary_paper(func)

    seven = seven_dimension_rows()
    write_csv(OUT / "rq2_seven_dimension_rates.csv", seven)
    draw_seven_dimension_lineplot(seven)

    rq3 = load_json(ROOT / "rq3_nfr_failure_top10.json")
    top10 = rq3["top10_metrics"]
    dim_fail = rq3["dimensions"]
    write_csv(
        OUT / "rq3_top_nfr_failures.csv",
        [
            {
                "rank": i + 1,
                "dimension": r["dimension"],
                "metric": r["metric"],
                "name": r["name"],
                "failed": r["failed"],
                "applicable": r["applicable"],
                "failure_rate": r["failure_rate"],
            }
            for i, r in enumerate(top10)
        ],
    )
    write_csv(OUT / "rq3_dimension_failures.csv", dim_fail)
    draw_rq3_top_failures_paper(top10)
    draw_rq3_dimension_failures_paper(dim_fail)

    summary = [
        "# 论文图片生成结果",
        "",
        "所有图片均由 `scripts/generate_paper_figures.py` 从本地实验数据生成。图内不包含论文 caption 式标题，标题请放在 LaTeX/Word 的图注中。",
        "",
        "| 图片 | Source data | Notes |",
        "|---|---|---|",
        f"| `{FIG_LANGUAGE_DISTRIBUTION}` | `rerun_all_project_summaries_v2.json`, `dataset/repo-list.manifest.json`, `generation_language.txt` | 81 个任务的原仓库语言与目标实现语言分布。 |",
        f"| `{FIG_FUNCTIONAL_SUMMARY}` | `rerun_all_project_summaries_v2.json` | 功能指标，分母只统计 `original_score_build_ok=true` 的项目。 |",
        f"| `{FIG_SEVEN_DIMENSION}` | functional rerun data + `nfr_corrected_summary.json` | FR 与修正后的 NFR 维度通过率。 |",
        f"| `{FIG_RQ3_DIMENSION_FAILURES}` | `rq3_nfr_failure_top10.json` | build-success 项目内的 NFR 维度失败率。 |",
        f"| `{FIG_RQ3_TOP_FAILURES}` | `rq3_nfr_failure_top10.json` | 高频 NFR 失败指标 Top 10。 |",
        "",
        "每张图片同时输出 `.svg` 和 `.png`；同目录 CSV 文件保存绘图数据。",
        "",
        "注：方法框架图不再生成；当前仅保留语言分布图和实验结果/缺陷分析图。",
    ]
    (OUT / "README.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    print(f"Generated figures in {OUT}")


if __name__ == "__main__":
    main()
