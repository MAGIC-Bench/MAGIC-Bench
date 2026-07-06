# -*- coding: utf-8 -*-
"""
code-bench-v2 数据集分析 → 详尽 HTML 报告
==========================================
读取:出卷包(卷面 meta)、成绩(grades/score.json)、候选提交(各 agent 源码)、
      元数据(原仓清单 manifest + 权威语言报告 report-lang),生成一份自包含的 HTML 报告。

用法:
    python analyze.py                # 包内运行(读相对目录:成绩/ 出卷包/ submissions/ 元数据/)
    python analyze.py --backup       # 本机生成用(直接读 D:\\code-bench-v2\\backup_clean)
"""
import json, os, sys, glob, html, datetime, collections

# ---------------------------------------------------------------- 路径配置(双模式)
HERE = os.path.dirname(os.path.abspath(__file__))
if "--backup" in sys.argv:
    B = r"D:\code-bench-v2\backup_clean"
    GRADES = os.path.join(B, "chuti-run", "grades")
    EXAMS = os.path.join(B, "chuti-run", "exams")
    SUBS = os.path.join(B, "chuti-run", "submissions")
    MANIFEST = r"D:\code-bench-v2\dataset\repo-list.manifest.json"
    REPORTLANG = r"D:\code-bench-v2\_report_lang.json"
else:
    GRADES = os.path.join(HERE, "成绩")
    EXAMS = os.path.join(HERE, "出卷包", "卷面-考生包")
    SUBS = os.path.join(HERE, "候选提交-各agent生成")
    MANIFEST = os.path.join(HERE, "元数据", "repo-list.manifest.json")
    REPORTLANG = os.path.join(HERE, "元数据", "report-lang.json")
OUT = os.path.join(HERE, "report.html")
CLI_INTERFACE_SUMMARY = os.path.join(HERE, "cli_interface_compliance_summary.json")

AGENTS = ["claude", "codex", "cursor", "kimi", "agy"]
MAIN = ["claude", "codex", "cursor", "kimi"]            # 主排名(agy 为网络受限基线,单列)
EXCLUDE_REPOS = {"dosisod-refurb"}                      # grader 丢失,不纳入横向比较
AGENT_LABEL = {"claude": "Claude Code", "codex": "Codex", "cursor": "Cursor",
               "kimi": "Kimi", "agy": "Antigravity (agy)"}
NFR_DIMS = ["CMP", "MTN", "PERF", "PTB", "RLY", "SEC"]
NFR_LABEL = {"CMP": "兼容性 CMP", "MTN": "可维护性 MTN", "PERF": "性能 PERF",
             "PTB": "可移植/构建 PTB", "RLY": "可靠性 RLY", "SEC": "安全性 SEC"}
EXT = {".go": "Go", ".py": "Python", ".rs": "Rust", ".ts": "TS", ".js": "JS", ".java": "Java",
       ".cpp": "C++", ".cc": "C++", ".cxx": "C++", ".c": "C", ".rb": "Ruby", ".cs": "C#",
       ".php": "PHP", ".kt": "Kotlin", ".swift": "Swift", ".scala": "Scala", ".pl": "Perl",
       ".ex": "Elixir", ".exs": "Elixir", ".ml": "OCaml", ".hs": "Haskell"}
SKIP = ("node_modules", "gomodcache", ".gocache", "/target/", ".venv", "/vendor/", ".cargo",
        ".rustup", ".gopath", "/_ref", "__pycache__", "/.git/", "/dist/", "/build/", ".ref-")

def canon(l):
    l = (l or "").strip().lower()
    return {"golang": "go", "javascript": "js", "typescript": "ts", "cpp": "c++",
            "csharp": "c#", "c#": "c#", "c++": "c++"}.get(l, l)

# ---------------------------------------------------------------- 加载数据
def load_json(p, default=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default

manifest = load_json(MANIFEST, [])
rows = manifest if isinstance(manifest, list) else manifest.get("repos", manifest.get("items", []))
MAN = {x["id"]: x for x in rows}
REP = load_json(REPORTLANG, {}) or {}
CLI_INTERFACE = load_json(CLI_INTERFACE_SUMMARY, {}) or {}

def dom_lang(work):
    cnt = {}
    if not os.path.isdir(work):
        return None, 0
    for root, dirs, files in os.walk(work):
        rp = root.replace("\\", "/")
        if any(s in rp + "/" for s in SKIP):
            dirs[:] = []
            continue
        for f in files:
            e = os.path.splitext(f)[1].lower()
            if e in EXT:
                cnt[EXT[e]] = cnt.get(EXT[e], 0) + 1
    if not cnt:
        return None, 0
    top = max(cnt, key=cnt.get)
    return canon(top), sum(cnt.values())

# 逐仓逐 agent 汇总
repos = sorted(set(os.path.basename(d) for d in glob.glob(os.path.join(GRADES, "*")) if os.path.isdir(d))
               - EXCLUDE_REPOS)
DATA = {}                                              # rid -> {meta..., agents:{a:{...}}}
for rid in repos:
    m = MAN.get(rid, {})
    meta = load_json(os.path.join(EXAMS, rid, "meta.json"), {}) or {}
    rep = REP.get(rid, {})
    rw = rep.get("rewrite", [])
    rec_first = canon(rw[0][0]) if rw else canon((m.get("_rewrite") or [{}])[0].get("lang"))
    entry = {
        "rid": rid,
        "orig": canon(rep.get("orig") or m.get("_lang")),
        "orig_raw": rep.get("orig") or m.get("_lang") or "?",
        "target": canon(meta.get("generation_language")),
        "target_raw": meta.get("generation_language") or "?",
        "rec_first": rec_first,
        "scenario": m.get("scenario", "?"),
        "scen_label": m.get("_scen_label", m.get("scenario", "?")),
        "sut": meta.get("scenario_type", m.get("scenario_type", "?")),
        "stars": m.get("_stars", 0),
        "tier": m.get("_tier", "?"),
        "desc": m.get("_desc", ""),
        "repo_full": m.get("_repo", rid),
        "has_grader": os.path.isdir(os.path.join(EXAMS, rid)),
        "agents": {},
    }
    for a in AGENTS:
        sc = load_json(os.path.join(GRADES, rid, a, "score.json"))
        submitted = os.path.isdir(os.path.join(SUBS, rid, a, "work"))
        if sc is None and not submitted:
            continue
        wrote, nfiles = dom_lang(os.path.join(SUBS, rid, a, "work"))
        nfr = (sc or {}).get("nfr_by_dimension", {}) or {}
        nfr_flat = {k: v for dim in nfr.values() for k, v in dim.items()}
        build_ok = bool((sc or {}).get("build_ok"))
        # build_ok=false 时 nfr_score 会把适用 NFR 统一写成 0；这些是构建门零填充，
        # 不是静态/运行 NFR 指标的实际测量结果，因此不计入 NFR 分母。
        nfr_ones = sum(1 for v in nfr_flat.values() if v == 1) if build_ok else 0
        nfr_total = sum(1 for v in nfr_flat.values() if v is not None) if build_ok else 0
        entry["agents"][a] = {
            "graded": sc is not None,
            "build_ok": build_ok,
            "func": (sc or {}).get("功能分"),
            "nfr": nfr,
            "nfr_ones": nfr_ones,
            "nfr_total": nfr_total,
            "wrote": wrote,
            "nfiles": nfiles,
        }
    DATA[rid] = entry

# ---------------------------------------------------------------- 聚合统计
def agent_stats(a, rids=None):
    full_scope = rids is None
    rids = rids or list(DATA)
    g = bok = perfect = 0; fsum = 0.0; ones = tot = 0; clone = wronglang = ok_lang = 0
    fvals = []
    for rid in rids:
        e = DATA[rid]["agents"].get(a)
        if not e or not e["graded"]:
            continue
        g += 1
        if e["build_ok"]:
            bok += 1
            f = e["func"] or 0
            fsum += f
            fvals.append(f)
            if f >= 0.999:
                perfect += 1
        ones += e["nfr_ones"]; tot += e["nfr_total"]
        w = e["wrote"]; orig = DATA[rid]["orig"]; tgt = DATA[rid]["target"]
        if w:
            if w == tgt:
                ok_lang += 1
            elif w == orig:
                clone += 1
            else:
                wronglang += 1
    if full_scope:
        cli = (CLI_INTERFACE.get("agents") or {}).get(a) or {}
        # CLI 接口兼容性并入 NFR/CMP：项目级二值，完全符合记 1；仅 build_ok=true 进入分母。
        ones += int(cli.get("fully_compliant_projects", 0) or 0)
        tot += int(cli.get("build_ok_projects", 0) or 0)
    return {"graded": g, "build_ok": bok, "build_rate": (bok / g if g else 0),
            "func_avg": (fsum / bok if bok else 0), "fsum": fsum, "func_den": bok, "perfect": perfect,
            "nfr_rate": (ones / tot if tot else 0), "nfr_ones": ones, "nfr_total": tot,
            "clone": clone, "wronglang": wronglang, "ok_lang": ok_lang, "fvals": fvals,
            "lang_detected": ok_lang + clone + wronglang}

STATS = {a: agent_stats(a) for a in AGENTS}

# ---------------------------------------------------------------- HTML 组件
def esc(s):
    return html.escape(str(s))

def bar(pct, color, w=120, label=None):
    pct = max(0, min(100, pct))
    lab = label if label is not None else f"{pct:.2f}%"
    return (f'<span class="bar" style="width:{w}px"><span class="fill" '
            f'style="width:{pct:.1f}%;background:{color}"></span>'
            f'<span class="barlab">{esc(lab)}</span></span>')

def minibar(pct, color, w=70):
    pct = max(0, min(100, pct))
    return (f'<span class="bar" style="width:{w}px;vertical-align:middle"><span class="fill" '
            f'style="width:{pct:.1f}%;background:{color}"></span></span>')

def rate_cell(num, den, color, w=70):
    """率单元格:小柱 + 明写 分子/分母 = 百分比(两位小数)"""
    pct = (num / den * 100) if den else 0
    return f'{minibar(pct, color, w)} <span class="raw">{num}/{den} = <b>{pct:.2f}%</b></span>'

def avg_cell(total, n, color, w=70, maxv=1.0):
    """均值单元格:小柱 + 明写 总和/个数 = 均值(四位小数)"""
    avg = (total / n) if n else 0
    return f'{minibar(avg / maxv * 100, color, w)} <span class="raw">{total:.2f}/{n} = <b>{avg:.4f}</b></span>'

COLORS = {"claude": "#d97757", "codex": "#10a37f", "cursor": "#6e56cf", "kimi": "#7c3aed",
          "agy": "#888"}

def svg_bars(title, items, fmt=lambda v: f"{v:.3f}", maxv=None, color_by_key=True):
    maxv = maxv or (max((v for _, v in items), default=1) or 1)
    h = 26; pad = 150; bw = 320
    out = [f'<svg viewBox="0 0 {pad+bw+70} {len(items)*h+10}" class="chart">']
    for i, (k, v) in enumerate(items):
        y = i * h + 8
        c = COLORS.get(k, "#4a90d9") if color_by_key else "#4a90d9"
        wpx = (v / maxv) * bw if maxv else 0
        out.append(f'<text x="{pad-8}" y="{y+13}" text-anchor="end" class="svglab">{esc(AGENT_LABEL.get(k,k))}</text>')
        out.append(f'<rect x="{pad}" y="{y}" width="{wpx:.1f}" height="18" rx="3" fill="{c}"/>')
        out.append(f'<text x="{pad+wpx+6}" y="{y+13}" class="svgval">{esc(fmt(v))}</text>')
    out.append('</svg>')
    return f'<div class="chartbox"><div class="chart-t">{esc(title)}</div>{"".join(out)}</div>'

# ---------------------------------------------------------------- 计算概览数字
total_subs = sum(1 for rid in DATA for a in DATA[rid]["agents"])
total_graded = sum(1 for rid in DATA for a in DATA[rid]["agents"] if DATA[rid]["agents"][a]["graded"])
n_repos = len(DATA)
scen_count = collections.Counter(DATA[rid]["scen_label"] for rid in DATA)
orig_count = collections.Counter(DATA[rid]["orig_raw"] for rid in DATA)
tgt_count = collections.Counter(DATA[rid]["target_raw"] for rid in DATA)
sut_count = collections.Counter(DATA[rid]["sut"] for rid in DATA)
man_sut = collections.Counter(x.get("scenario_type") for x in rows)
svc_repos = [x for x in rows if x.get("scenario_type") == "service"]
svc_in_exam = sum(1 for x in svc_repos if x["id"] in DATA)
svc_stateful = sum(1 for x in svc_repos if "stateful" in (x.get("_friction") or x.get("friction") or []))

now = "GEN_TIME"

# ---------------------------------------------------------------- 生成 HTML
P = []
def w(s): P.append(s)

w(f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>code-bench-v2 数据集分析报告</title>
<style>
:root{{--bg:#0f1115;--card:#181b22;--card2:#1f232c;--bd:#2a2f3a;--fg:#e6e8ec;--mut:#9aa3b2;--acc:#4a90d9;}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:14px/1.6 -apple-system,"Segoe UI",Roboto,"Microsoft YaHei",sans-serif}}
.wrap{{max-width:1180px;margin:0 auto;padding:28px 22px 80px}}
h1{{font-size:30px;margin:0 0 4px}} h2{{font-size:21px;margin:38px 0 14px;padding-bottom:8px;border-bottom:2px solid var(--bd)}}
h3{{font-size:16px;margin:22px 0 10px;color:#cdd3dd}}
.sub{{color:var(--mut);margin:0 0 22px}}
.cards{{display:flex;flex-wrap:wrap;gap:12px;margin:18px 0}}
.card{{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px 18px;min-width:130px;flex:1}}
.card .n{{font-size:28px;font-weight:700}} .card .l{{color:var(--mut);font-size:12px;margin-top:2px}}
table{{border-collapse:collapse;width:100%;margin:10px 0 4px;font-size:13px}}
th,td{{border:1px solid var(--bd);padding:7px 10px;text-align:left;vertical-align:middle}}
th{{background:var(--card2);position:sticky;top:0;cursor:pointer;user-select:none}}
tr:nth-child(even) td{{background:#14171d}}
.bar{{display:inline-block;position:relative;height:16px;background:#0c0e12;border-radius:3px;vertical-align:middle;overflow:hidden}}
.fill{{position:absolute;left:0;top:0;height:100%;border-radius:3px}}
.barlab{{position:absolute;left:6px;top:-1px;font-size:11px;color:#fff;text-shadow:0 0 3px #000;line-height:18px}}
.chartbox{{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px 16px;margin:12px 0}}
.chart-t{{font-weight:600;margin-bottom:6px}} .chart{{width:100%;max-width:560px}}
.svglab{{fill:var(--fg);font-size:12px}} .svgval{{fill:var(--mut);font-size:11px}}
.tag{{display:inline-block;padding:1px 7px;border-radius:10px;font-size:11px;background:#262b34;color:#cdd3dd}}
.ok{{color:#4ade80}} .no{{color:#f87171}} .mut{{color:var(--mut)}} .warn{{color:#fbbf24}}
.note{{background:#1a1d24;border-left:3px solid var(--acc);padding:10px 14px;border-radius:0 6px 6px 0;margin:12px 0;color:#cdd3dd}}
.note.warn{{border-color:#fbbf24}} .note.bad{{border-color:#f87171}}
code{{background:#0c0e12;padding:1px 5px;border-radius:4px;font-size:12px}}
.heat td{{text-align:center}}
.legend{{color:var(--mut);font-size:12px;margin:6px 0}}
.small{{font-size:12px;color:var(--mut)}}
.raw{{font-size:12px;color:#cdd3dd;white-space:nowrap}}
.flex{{display:flex;gap:18px;flex-wrap:wrap;align-items:flex-start}}
</style></head><body><div class="wrap">""")

w(f"<h1>code-bench-v2 数据集分析报告</h1>")
w(f'<p class="sub">黑盒差分跨语言基准 · 生成时间 {now}</p>')

# —— 概览卡片
w('<div class="cards">')
for n, l in [(n_repos, "题目(仓库)"), (len(MAIN), "主测 Agent"), (total_subs, "候选提交总数"),
             (total_graded, "已判提交"), (len(scen_count), "场景类型"), (len(orig_count), "原语言种类")]:
    w(f'<div class="card"><div class="n">{n}</div><div class="l">{esc(l)}</div></div>')
w('</div>')

# —— 方法学
w('<h2>① 方法学</h2>')
w("""<div class="note">
<b>这是什么基准</b>:每道题取一个真实开源仓库(原语言 X),让多个 AI 编程 Agent <b>用另一种目标语言 Y 从零重写</b>,
仅依据卷面给出的<b>对外可观察行为契约</b>(项目描述 / API 手册 / 用户故事 / 非功能需求 / 机器可读 CLI 契约)实现,
<b>看不到原仓源码</b>。判卷为<b>黑盒差分</b>:把候选与"原仓跑出的 golden"在相同输入下对比。
</div>""")
w("""<table><tr><th>评分项</th><th>含义</th></tr>
<tr><td><b>build_ok</b></td><td>候选能否构建 + 冒烟(smoke)跑起来。失败则功能分归零，并单独计入构建失败。</td></tr>
<tr><td><b>功能分</b></td><td>单项目差分测试用例的通过率(0~1):候选对外行为与 golden 一致的比例。报告中的平均功能分只对 build_ok=true 的项目做宏平均，构建失败项目不进入功能分分母。</td></tr>
<tr><td><b>NFR</b></td><td>非功能需求,6 个维度逐指标 0/1(null=该指标不适用)。NFR 满足率只统计 build_ok=true 后实际测得的非 null 指标；build_ok=false 的零填充不进入 NFR 分母。CLI 接口契约完全符合项目作为 CMP 兼容性二值指标并入统计。
CMP 兼容性 · MTN 可维护性 · PERF 性能 · PTB 可移植/构建 · RLY 可靠性 · SEC 安全性。</td></tr>
</table>""")

# —— 数据集构成
w('<h2>② 数据集构成</h2>')
w('<div class="flex">')
def dist_table(title, counter, total):
    rows = sorted(counter.items(), key=lambda kv: -kv[1])
    mx = max((c for _, c in rows), default=1)
    s = [f'<div style="flex:1;min-width:320px"><h3>{esc(title)}</h3>'
         f'<table><tr><th>类别</th><th>题数/总数 = 占比</th></tr>']
    for k, c in rows:
        s.append(f'<tr><td>{esc(k)}</td><td>{minibar(c/mx*100,"#4a90d9",150)} '
                 f'<span class="raw">{c}/{total} = <b>{c/total*100:.2f}%</b></span></td></tr>')
    s.append('</table></div>')
    return "".join(s)
w(dist_table("场景分布", scen_count, n_repos))
w(dist_table("SUT 类型(被测程序形态)", sut_count, n_repos))
w('</div><div class="flex">')
w(dist_table("原语言分布", orig_count, n_repos))
w(dist_table("目标语言(我们要求改写成的)", tgt_count, n_repos))
w('</div>')

# 原→目标 迁移
w('<h3>原语言 → 目标语言 迁移</h3>')
mig = collections.Counter((DATA[rid]["orig_raw"], DATA[rid]["target_raw"]) for rid in DATA)
w('<table><tr><th>原语言</th><th>目标语言</th><th>题数</th></tr>')
for (o, t), c in sorted(mig.items(), key=lambda kv: -kv[1]):
    w(f'<tr><td>{esc(o)}</td><td>{esc(t)}</td><td>{c}</td></tr>')
w('</table>')

# 为什么全 cli、没 service —— 代码级溯源(修正:不是有意排除,是栽在健全性门)
w('<h3>为什么 SUT 全是 cli、没有 service?(出题了,却栽在"出卷健全性门")</h3>')
w(f'''<div class="note bad">
<b>结论(代码溯源)</b>:清单里有 <b>{man_sut.get("service",0)} 个 service 仓</b>,但<b>无一进入最终数据集
({svc_in_exam}/{len(svc_repos)})</b>。它们<b>不是被选题时过滤掉的,而是都出了题、却产不出"可复现的 golden",
栽在健全性门 <code>gate_stage7</code> 上</b>。根因:<b>有状态服务在出题流水线里缺少"每次重跑前把状态重置到一致初始态"的机制</b>。</div>''')
w(f'''<div class="note">
<b>证据链(全部来自本基准代码)</b>:
<ol style="margin:6px 0 0">
<li><b>service 被尝试出题、未预先过滤</b>:<code>run/launch_chuti.sh</code> 枚举清单<b>全部 {len(rows)} 仓</b>(含 {man_sut.get("service",0)} 个 service),无 scenario_type/friction 过滤;<code>engine/gates.py · gate_stage1</code> 明确允许 <code>scenario_type ∈ cli|service|pipeline</code>;<code>engine/harness.py</code> 注释"enabling … service/pipeline for the dataset";判卷侧 <code>_grade.py</code> 备有完整的 <code>LocalService</code> + <code>run_service_cases</code> + <code>http:</code> 断言字段。<b>service 是一等公民,本该能测。</b></li>
<li><b>出卷健全性要求"原仓能复现自己的 golden"</b>:<code>classify.py · agrees()</code> —— golden 捕获时把原仓<b>同一输入跑两遍,只有两遍一致(确定性)的用例才冻结</b>;<code>gate_stage7</code> —— 再用原仓重跑自己的 golden,<b>丢弃率 &gt;5%(原仓通不过自己 golden)或无幸存用例即判废</b>。</li>
<li><b>有状态服务过不了这两关</b>:服务输出依赖<b>累积状态</b>(数据库行 / 已创建资源 / 会话);第二遍带着第一遍的写入 → 两遍<b>不一致</b> → 用例被 <code>agrees</code> 丢 + 原仓重跑对不上自己 golden → <code>gate_stage7</code> 丢弃率飙升 → <b>整道判废、进 SKIP</b>(launch_chuti 注释:"golden 不可靠,原仓做不出干净基准")。</li>
<li><b>流水线确实没有"重置状态"环节</b>:<code>engine/runner.py · _snapshot()</code> 只快照<b>工作目录文件</b>(捕获文件型输出),<b>不重置服务持久状态</b>;判卷侧 <code>restart()</code> 注释直白:<b>"keep the data dir (dirty restart)" —— 重启故意保留数据目录、不清状态</b>。全流程没有"快照初始态 → 每次重跑前还原"的机制。</li>
</ol></div>''')
w('''<div class="note warn">
<b>这能避免吗?能,但没做。</b> 原则上只要在每次确定性重跑前把服务状态<b>快照 → 还原到初始态</b>(清库 / 还原数据目录 / 重置已创建资源),有状态服务就能产出可复现 golden、通过 gate_stage7。
难在<b>通用化</b>:每个服务存状态的方式不同(库 / 文件 / 内存),流水线没有为每个 service 仓生成"状态快照+还原"的 RESET 钩子,故有状态服务全部落选。
<b>所以本数据集"全 cli"是这条流水线局限的产物、而非有意排除——harness 本身支持 service,是 golden 生成环节复现不了有状态 SUT。</b></div>''')
if svc_repos:
    dom = collections.Counter(x.get("scenario", "?") for x in svc_repos)
    w('<p class="small">被判废的 22 个 service 仓按领域:' +
      " · ".join(f"{esc(k)} {c}" for k, c in dom.most_common()) + '</p>')

# —— Agent 综合排名
w('<h2>③ Agent 综合排名</h2>')
ranked = sorted(MAIN, key=lambda a: -STATS[a]["func_avg"])
w('<p class="legend">每个"率"都写出 <b>分子/分母 = 百分比(两位小数)</b>;平均功能分写出 <b>功能分总和/构建成功数 = 均值</b>。'
  '<br>构建通过率 = 构建成功数 / 已判数 · 满分率 = 满分卷数 / 构建成功数 · NFR满足率 = 满足指标数 / 适用指标数 · 平均功能分 = Σ功能分 / 构建成功数</p>')
w('<table><tr><th>#</th><th>Agent</th><th>已判<br><span class="small">(分母)</span></th><th>平均功能分<br>'
  '<span class="small">Σ功能分/构建成功</span></th><th>构建通过率<br><span class="small">成功/已判</span></th>'
  '<th>满分率<br><span class="small">满分/构建成功</span></th><th>NFR满足率<br><span class="small">满足/适用</span></th></tr>')
def rank_row(idx, a, col):
    s = STATS[a]
    return (f'<tr><td>{idx}</td><td><b>{esc(AGENT_LABEL[a])}</b>{" <span class=tag>网络受限基线</span>" if a=="agy" else ""}</td>'
            f'<td>{s["graded"]}</td>'
            f'<td>{avg_cell(s["fsum"], s["func_den"], col)}</td>'
            f'<td>{rate_cell(s["build_ok"], s["graded"], "#4a90d9")}</td>'
            f'<td>{rate_cell(s["perfect"], s["func_den"], "#eab308")}</td>'
            f'<td>{rate_cell(s["nfr_ones"], s["nfr_total"], "#10a37f")}</td></tr>')
for i, a in enumerate(ranked, 1):
    w(rank_row(i, a, COLORS[a]))
w(rank_row("—", "agy", COLORS["agy"]))
w('</table>')
w('<div class="flex">')
w(svg_bars("平均功能分", [(a, STATS[a]["func_avg"]) for a in ranked], maxv=1))
w(svg_bars("构建通过率", [(a, STATS[a]["build_rate"]) for a in ranked], fmt=lambda v: f"{v*100:.0f}%", maxv=1))
w('</div>')

# —— 功能分分布
w('<h2>④ 功能分分布</h2>')
w('<p class="legend">每个 Agent 的功能分落在各区间的卷数(看满分/零分/部分分的形态)</p>')
buckets = [(0, 0.001, "0(零分)"), (0.001, 0.25, "0–0.25"), (0.25, 0.5, "0.25–0.5"),
           (0.5, 0.75, "0.5–0.75"), (0.75, 0.999, "0.75–<1"), (0.999, 1.01, "1.0(满分)")]
w('<table><tr><th>Agent</th>' + "".join(f"<th>{esc(b[2])}</th>" for b in buckets) + '</tr>')
for a in MAIN:
    fv = STATS[a]["fvals"]
    w(f'<tr><td><b>{esc(AGENT_LABEL[a])}</b></td>')
    for lo, hi, _ in buckets:
        c = sum(1 for v in fv if lo <= v < hi)
        sh = "background:#1d3a2e" if _ == "1.0(满分)" and c else ("background:#3a1d1d" if _ == "0(零分)" and c else "")
        w(f'<td style="text-align:center;{sh}">{c}</td>')
    w('</tr>')
w('</table>')

# —— NFR 维度热力
w('<h2>⑤ NFR 各维度满足率</h2>')
w('<p class="legend">每个维度:满足(=1)的指标数 / build_ok=true 后实际可测的非 null 指标数。build_ok=false 的硬门零填充不计入分母。CMP 兼容性额外并入 CLI 接口契约二值指标:完全符合项目=1，否则=0。</p>')
def nfr_rate_dim(a, dim):
    ones = tot = 0
    for rid in DATA:
        e = DATA[rid]["agents"].get(a)
        if not e or not e["graded"] or not e["build_ok"]:
            continue
        d = e["nfr"].get(dim, {})
        for v in d.values():
            if v is not None:
                tot += 1
                if v == 1:
                    ones += 1
    if dim == "CMP":
        cli = (CLI_INTERFACE.get("agents") or {}).get(a) or {}
        ones += int(cli.get("fully_compliant_projects", 0) or 0)
        tot += int(cli.get("build_ok_projects", 0) or 0)
    return ones, tot
w('<table class="heat"><tr><th>Agent</th>' + "".join(f"<th>{esc(NFR_LABEL[d])}</th>" for d in NFR_DIMS) + '<th>总计</th></tr>')
for a in MAIN + ["agy"]:
    w(f'<tr><td style="text-align:left"><b>{esc(AGENT_LABEL[a])}</b></td>')
    to_o = to_t = 0
    for d in NFR_DIMS:
        o, t = nfr_rate_dim(a, d); to_o += o; to_t += t
        r = (o / t) if t else 0
        g = int(60 + r * 120); rr = int(180 - r * 120)
        bg = f"background:rgb({rr},{g},70)" if t else "background:#222"
        txt = f"{o}/{t}<br>{r*100:.2f}%" if t else "—"
        w(f'<td style="{bg};color:#0c0e12;font-weight:600">{txt}</td>')
    rr = (to_o / to_t) if to_t else 0
    w(f'<td style="font-weight:700">{to_o}/{to_t}<br>{rr*100:.2f}%</td></tr>')
w('</table>')

# —— 按场景细分
w('<h2>⑥ 按场景细分(平均功能分)</h2>')
scens = sorted(set(DATA[rid]["scen_label"] for rid in DATA))
w('<table><tr><th>场景</th><th>题数</th>' + "".join(f"<th>{esc(AGENT_LABEL[a])}</th>" for a in MAIN) + '</tr>')
for sc in scens:
    rids = [rid for rid in DATA if DATA[rid]["scen_label"] == sc]
    w(f'<tr><td>{esc(sc)}</td><td>{len(rids)}</td>')
    for a in MAIN:
        st = agent_stats(a, rids)
        w(f'<td>{avg_cell(st["fsum"], st["func_den"], COLORS[a], 55)}</td>')
    w('</tr>')
w('</table>')

# —— 按目标语言细分
w('<h2>⑦ 按目标语言细分(平均功能分)</h2>')
tgts = sorted(set(DATA[rid]["target_raw"] for rid in DATA))
w('<table><tr><th>目标语言</th><th>题数</th>' + "".join(f"<th>{esc(AGENT_LABEL[a])}</th>" for a in MAIN) + '</tr>')
for tg in tgts:
    rids = [rid for rid in DATA if DATA[rid]["target_raw"] == tg]
    w(f'<tr><td>{esc(tg)}</td><td>{len(rids)}</td>')
    for a in MAIN:
        st = agent_stats(a, rids)
        w(f'<td>{avg_cell(st["fsum"], st["func_den"], COLORS[a], 55)}</td>')
    w('</tr>')
w('</table>')

# —— 语言一致性 / 克隆
w('<h2>⑧ 语言一致性与"克隆原仓"现象</h2>')
w("""<div class="note warn"><b>发现</b>:判卷只对比对外行为、<b>不校验候选用的是什么语言</b>。
于是部分 Agent 直接 <code>git clone</code> 原仓(写成<b>原语言</b>)糊弄,而因为原仓本就能跑,
还能拿到功能分——这是黑盒差分基准的一个可被钻的空子。</div>""")
w('<p class="legend">一致率 = 写对数 / 检测到语言的提交数;克隆率 = 写成原语言数 / 检测到语言的提交数(两位小数)。</p>')
w('<table><tr><th>Agent</th><th>检测数<br><span class="small">(分母)</span></th>'
  '<th>写对(=目标语言)</th><th>写成原语言(疑似克隆)</th><th>写成第三种语言</th></tr>')
for a in MAIN:
    s = STATS[a]; det = s["lang_detected"] or 1
    w(f'<tr><td><b>{esc(AGENT_LABEL[a])}</b></td><td>{s["lang_detected"]}</td>'
      f'<td class="ok">{s["ok_lang"]} <span class="raw">{s["ok_lang"]}/{s["lang_detected"]} = {s["ok_lang"]/det*100:.2f}%</span></td>'
      f'<td class="no">{s["clone"]} <span class="raw">{s["clone"]}/{s["lang_detected"]} = {s["clone"]/det*100:.2f}%</span></td>'
      f'<td class="warn">{s["wronglang"]} <span class="raw">{s["wronglang"]}/{s["lang_detected"]} = {s["wronglang"]/det*100:.2f}%</span></td></tr>')
w('</table>')
# 列出克隆卷
clones = []
for rid in DATA:
    for a in MAIN:
        e = DATA[rid]["agents"].get(a)
        if e and e["graded"] and e["wrote"] and e["wrote"] == DATA[rid]["orig"] and e["wrote"] != DATA[rid]["target"]:
            clones.append((a, rid, DATA[rid]["orig_raw"], DATA[rid]["target_raw"], e["func"]))
if clones:
    w('<h3>疑似克隆原仓的提交(及其功能分 — 看有没有靠克隆骗到分)</h3>')
    w('<table><tr><th>Agent</th><th>题目</th><th>原语言</th><th>要求写</th><th>实际写</th><th>功能分</th></tr>')
    for a, rid, o, t, f in sorted(clones, key=lambda x: -(x[4] or 0)):
        cls = "no" if (f or 0) >= 0.8 else ""
        w(f'<tr><td>{esc(AGENT_LABEL[a])}</td><td>{esc(rid)}</td><td>{esc(o)}</td><td>{esc(t)}</td>'
          f'<td class="warn">{esc(o)}</td><td class="{cls}">{f if f is not None else "—"}</td></tr>')
    w('</table>')

# —— 逐仓详情
w('<h2>⑨ 逐仓详情</h2>')
w('<p class="legend">点表头排序。每格:✓/✗=构建, 数字=功能分, 括号=该 agent 实际写的语言。</p>')
w('<table id="repos"><thead><tr>'
  '<th>题目</th><th>原语言</th><th>目标</th><th>场景</th><th>★</th>'
  + "".join(f"<th>{esc(AGENT_LABEL[a])}</th>" for a in AGENTS) + '</tr></thead><tbody>')
for rid in sorted(DATA, key=lambda r: -sum((DATA[r]["agents"].get(a, {}) or {}).get("func") or 0 for a in MAIN)):
    e = DATA[rid]
    w(f'<tr><td title="{esc(e["desc"])}">{esc(rid)}</td><td>{esc(e["orig_raw"])}</td>'
      f'<td>{esc(e["target_raw"])}</td><td>{esc(e["scenario"])}</td><td>{e["stars"] or ""}</td>')
    for a in AGENTS:
        ag = e["agents"].get(a)
        if not ag or not ag["graded"]:
            w('<td class="mut">—</td>'); continue
        b = '<span class="ok">✓</span>' if ag["build_ok"] else '<span class="no">✗</span>'
        f = ag["func"]
        wl = ag["wrote"] or "?"
        flag = ' style="background:#3a1d1d"' if (wl == e["orig"] and wl != e["target"]) else ""
        w(f'<td{flag}>{b} {f:.2f} <span class="small">({esc(wl)})</span></td>' if f is not None
          else f'<td>{b} —</td>')
    w('</tr>')
w('</tbody></table>')

# —— 已知局限
w('<h2>⑩ 方法学局限与已知问题</h2>')
w("""<div class="note">本数据集在判卷流程中发现并修复了两个会<b>系统性压低分数</b>的 bug,报告中的分数为<b>修复后</b>的真实分:</div>""")
w("""<ul>
<li><b>判卷 bug ①(launch 路径)</b>:做题节点把启动命令写成本地绝对路径,判卷在另一节点重建后路径没重写 →
候选构建成功却"跑不起来" → build_ok 误判为 false → 功能分及 NFR 全归零。修复后大量"构建失败"翻案
(例:cursor 一度看着垫底,真实是并列第一)。</li>
<li><b>判卷 bug ②(cwd 竞态)</b>:判卷 worker 删临时目录前没切出去,下一轮在已删目录里启动 grade.py 偶发崩溃 → 兜底判 0。已修。</li>
<li><b>smoke 门偏严</b>:个别题用 <code>--version</code>、help 走 stdout/stderr 等细节做冒烟门,合理的重写实现因缺这种小特性被判 0
(约 10 个仓全员 0 分属此类)。按"测试不过分苛刻"的原则保留现状,报告中标注。</li>
<li><b>1 道题 grader 丢失</b>(dosisod-refurb 出题只到 baseline 阶段)→ 该题无法判卷,有效题数 81。</li>
<li><b>agy(Antigravity)网络受限</b>:无稳定 Gemini 代理,228+ 次"等响应超时",原始运行中只完成约 53 道、仅 3 道构建成功 →
作为"被墙 Agent 的基线"参考,不参与主排名。</li>
</ul>""")

w(f'<p class="small" style="margin-top:40px">报告由 analyze.py 自动生成 · 数据源:成绩 {GRADES} · 共 {n_repos} 题 / {total_graded} 已判提交</p>')

# 排序脚本
w("""<script>
document.querySelectorAll('#repos thead th').forEach((th,i)=>{th.addEventListener('click',()=>{
 const tb=document.querySelector('#repos tbody');const rows=[...tb.rows];
 const asc=th._asc=!th._asc;
 rows.sort((a,b)=>{let x=a.cells[i].innerText.replace(/[^\\d.\\-]/g,''),y=b.cells[i].innerText.replace(/[^\\d.\\-]/g,'');
  if(x!==''&&y!==''&&!isNaN(x)&&!isNaN(y))return asc?x-y:y-x;
  return asc?a.cells[i].innerText.localeCompare(b.cells[i].innerText):b.cells[i].innerText.localeCompare(a.cells[i].innerText);});
 rows.forEach(r=>tb.appendChild(r));});});
</script>""")

w('</div></body></html>')

stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
out_html = "".join(P).replace("GEN_TIME", stamp)
open(OUT, "w", encoding="utf-8").write(out_html)
print(f"OK -> {OUT}")
print(f"题数={n_repos} 已判={total_graded} 提交={total_subs}")
for a in AGENTS:
    s = STATS[a]
    print(f"  {a:7} 判{s['graded']:>3} 功能{s['func_avg']:.4f}(Σ{s['fsum']:.2f}/{s['func_den']}) "
          f"构建{s['build_ok']}/{s['graded']}={s['build_rate']*100:.2f}% 满分{s['perfect']}/{s['func_den']} "
          f"NFR{s['nfr_ones']}/{s['nfr_total']}={s['nfr_rate']*100:.2f}% 克隆{s['clone']}")
